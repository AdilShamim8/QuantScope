"""
LLM engine and provider failover logic.

This module:
    1. Detects which LLM providers are configured via environment variables.
    2. Builds provider-specific chat clients.
    3. Sends prompts and returns text responses.
    4. Automatically fails over to another provider if one fails.
"""

import logging
import os
import requests
from langchain_core.messages import HumanMessage, SystemMessage
from config import settings

logger = logging.getLogger(__name__)


class _Msg:
    """Small response wrapper to match expected `.content` access pattern."""

    def __init__(self, content):
        self.content = content


class _OllamaChat:
    """Minimal Ollama chat client compatible with the engine's invoke contract."""

    def __init__(self, model, base_url, temperature, timeout):
        self._model = model
        self._base = (base_url or "http://localhost:11434").rstrip("/")
        self._temp = temperature
        self._timeout = timeout
        self._api_key = os.environ.get("OLLAMA_API_KEY", "").strip()

    def invoke(self, msgs):
        # Convert LangChain message objects into Ollama API role/content format.
        mapped = []
        for m in msgs:
            role = "user"
            if isinstance(m, SystemMessage):
                role = "system"
            elif isinstance(m, HumanMessage):
                role = "user"
            mapped.append({"role": role, "content": m.content})

        # Optional bearer auth if user has secured Ollama gateway.
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = "Bearer {}".format(self._api_key)

        # Non-streaming chat call so we can return a single final string.
        payload = {
            "model": self._model,
            "messages": mapped,
            "stream": False,
            "options": {"temperature": self._temp},
        }

        # Call Ollama HTTP endpoint and normalize output shape.
        r = requests.post(
            self._base + "/api/chat",
            json=payload,
            headers=headers,
            timeout=self._timeout,
        )
        r.raise_for_status()
        data = r.json() if r.content else {}
        text = ((data.get("message") or {}).get("content") or "").strip()
        return _Msg(text)


def _providers():
    """Build ordered list of configured providers from settings + environment."""

    out = []
    # Preserve configured preference order so first valid provider becomes primary.
    for name in settings.LLM_ORDER:
        model = settings.LLM_MODELS.get(name)
        if not model:
            continue
        # Add provider only if required API credentials/config are available.
        if name == "openai" and os.environ.get("OPENAI_API_KEY"):
            out.append({"name": name, "model": model})
        elif name == "anthropic" and os.environ.get("ANTHROPIC_API_KEY"):
            out.append({"name": name, "model": model})
        elif name == "google" and os.environ.get("GOOGLE_API_KEY"):
            out.append({"name": name, "model": model})
        elif name == "ollama" and (
            os.environ.get("OLLAMA_BASE_URL") or os.environ.get("OLLAMA_API_KEY")
        ):
            out.append({
                "name": name,
                "model": model,
                "url": os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
            })
        elif name == "mistral" and os.environ.get("MISTRAL_API_KEY"):
            out.append({"name": name, "model": model})
        elif name == "cohere" and os.environ.get("COHERE_API_KEY"):
            out.append({"name": name, "model": model})
    return out


def _make(p):
    """Create provider-specific chat client instance from provider metadata."""

    try:
        n, m = p["name"], p["model"]
        kw = {"temperature": settings.LLM_TEMP, "max_tokens": settings.LLM_TOKENS}
        if n == "openai":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(model=m, request_timeout=settings.LLM_TIMEOUT, **kw)
        if n == "anthropic":
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(model=m, timeout=settings.LLM_TIMEOUT, **kw)
        if n == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(model=m, max_output_tokens=kw["max_tokens"],
                                           temperature=kw["temperature"])
        if n == "ollama":
            return _OllamaChat(
                model=m,
                base_url=p.get("url", "http://localhost:11434"),
                temperature=kw["temperature"],
                timeout=settings.LLM_TIMEOUT,
            )
        if n == "mistral":
            from langchain_community.chat_models import ChatMistralAI
            return ChatMistralAI(model=m, **kw)
        if n == "cohere":
            from langchain_community.chat_models import ChatCohere
            return ChatCohere(model=m, **kw)
    except Exception as e:
        # Keep app running even if one provider cannot initialize.
        logger.warning("Cannot init %s: %s", p["name"], e)
    return None


class LLMEngine:
    """
    High-level LLM manager with automatic provider bootstrapping and failover.

    Usage:
      - Initialize once.
      - Call `invoke(system_prompt, user_prompt)`.
      - Engine will use active provider or switch on failure.
    """

    def __init__(self):
        # Build candidate providers in preferred order.
        self._chain = _providers()
        self._active = None
        self._model = None
        if self._chain:
            logger.info("LLM providers: %s", [p["name"] for p in self._chain])
            # Boot first available provider model.
            self._boot()
        else:
            logger.warning("No LLM configured. Template fallback active.")

    @property
    def available(self):
        """True when an active model instance is ready to serve requests."""
        return self._model is not None

    @property
    def provider(self):
        """Current active provider name, or 'none' if unavailable."""
        return self._active or "none"

    def invoke(self, system, user):
        """Send prompt pair to active provider, with automatic fallback across providers."""

        if not self._chain:
            return None
        msgs = [SystemMessage(content=system), HumanMessage(content=user)]

        # First try currently active provider for best performance.
        if self._model:
            r = self._try(self._active, self._model, msgs)
            if r:
                return r

        # If active provider fails, walk remaining providers until one succeeds.
        for p in self._chain:
            if p["name"] == self._active:
                continue
            m = _make(p)
            if not m:
                continue
            r = self._try(p["name"], m, msgs)
            if r:
                # Promote successful provider as new active default.
                self._active = p["name"]
                self._model = m
                logger.info("Switched LLM to %s", p["name"])
                return r
        return None

    def _try(self, name, model, msgs):
        """Attempt one provider call and return normalized text or None on failure."""

        try:
            resp = model.invoke(msgs)
            txt = resp.content
            # Guard against empty/trivial responses.
            if txt and len(txt.strip()) > 10:
                return txt.strip()
        except Exception as e:
            logger.warning("LLM %s failed: %s", name, e)
        return None

    def _boot(self):
        """Initialize first provider that can be constructed successfully."""

        for p in self._chain:
            m = _make(p)
            if m:
                self._active = p["name"]
                self._model = m
                logger.info("Active LLM: %s", p["name"])
                return