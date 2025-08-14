awesome — here’s a clean, “drop-in” set of JSON specs you can use for:

1. an **OpenAI-compatible** connection form
2. an **Ollama** connection form
3. **per-chat controls** your UI can surface (sliders/toggles)
4. **request body templates** that show exactly how to wire the outputs into each provider

I’ve annotated each field with descriptions and provider support, so you can selectively exclude “exotic” params when a backend doesn’t support them.

---

# 1) OpenAI-compatible connection form (covers OpenAI, Azure OpenAI, and providers that mimic the OpenAI API)

```json
{
  "type": "openai_compatible_connection",
  "fields": {
    "base_url": {
      "type": "string",
      "default": "https://api.openai.com/v1",
      "description": "Root API URL. For Azure/OpenAI-compatible vendors, set their base endpoint."
    },
    "api_key": {
      "type": "secret",
      "required": true,
      "description": "Bearer token used for Authorization header."
    },
    "organization": {
      "type": "string",
      "required": false,
      "description": "Optional OpenAI org header (OpenAI-Organization)."
    },
    "project": {
      "type": "string",
      "required": false,
      "description": "Optional OpenAI project header (OpenAI-Project)."
    },
    "api_type": {
      "type": "enum",
      "values": ["openai", "azure", "other"],
      "default": "openai",
      "description": "Needed to shape paths/headers (Azure uses a different URL shape and api-version)."
    },
    "api_version": {
      "type": "string",
      "required": false,
      "description": "For Azure/OpenAI-compatible vendors that require an api-version query param."
    },
    "deployment": {
      "type": "string",
      "required": false,
      "description": "Azure only: the deployment name (used in URL path instead of a model name)."
    },
    "default_model": {
      "type": "string",
      "required": true,
      "description": "Model ID (e.g., gpt-4.1, gpt-4o, etc.) or Azure deployment name."
    },
    "compatibility_mode": {
      "type": "enum",
      "values": ["responses", "chat_completions"],
      "default": "responses",
      "description": "Prefer Responses API for new builds; fall back to Chat Completions when required."
    },
    "stream": {
      "type": "boolean",
      "default": true,
      "description": "Enable SSE streaming if supported."
    },
    "timeout_ms": {
      "type": "number",
      "default": 60000,
      "description": "Client request timeout."
    },
    "extra_headers": {
      "type": "object",
      "default": {},
      "description": "Arbitrary header overrides/ additions."
    }
  }
}
```

Why these fields: OpenAI’s **Responses** API is the primary modern interface, with Chat Completions still supported; many “OpenAI-compatible” vendors mimic one or both. Azure requires custom pathing + `api-version`. ([GitHub][1], [OpenAI Platform][2], [Microsoft Learn][3])

---

# 2) Ollama connection form

```json
{
  "type": "ollama_connection",
  "fields": {
    "host": {
      "type": "string",
      "default": "http://localhost:11434",
      "description": "Ollama server base URL."
    },
    "route": {
      "type": "enum",
      "values": ["/api/chat", "/api/generate"],
      "default": "/api/chat",
      "description": "Use /api/chat for message arrays; /api/generate for single-prompt completion."
    },
    "model": {
      "type": "string",
      "required": true,
      "description": "Local model name, e.g. llama3:8b or mistral:7b."
    },
    "stream": {
      "type": "boolean",
      "default": true,
      "description": "Stream partial tokens."
    },
    "keep_alive": {
      "type": "string",
      "default": "5m",
      "description": "Keep model in memory after requests (e.g., 5m, 0 to unload)."
    },
    "format": {
      "type": "enum_or_null",
      "values": ["json", null],
      "default": null,
      "description": "Enable JSON mode. Remember to also instruct the model to answer in JSON."
    },
    "options": {
      "type": "object",
      "description": "Sampling/runtime options passed under `options`.",
      "properties": {
        "temperature": { "type": "number", "default": 0.8 },
        "top_p": { "type": "number", "default": 0.9 },
        "top_k": { "type": "number", "default": 40 },
        "min_p": { "type": "number", "default": 0.0 },
        "num_predict": { "type": "number", "default": 128 },
        "num_ctx": { "type": "number", "default": 2048 },
        "seed": { "type": "number", "default": 0 },
        "repeat_penalty": { "type": "number", "default": 1.1 },
        "repeat_last_n": { "type": "number", "default": 64 },
        "tfs_z": { "type": "number", "default": 1.0 },
        "mirostat": { "type": "integer", "default": 0 },
        "mirostat_tau": { "type": "number", "default": 5.0 },
        "mirostat_eta": { "type": "number", "default": 0.1 },
        "stop": { "type": "array", "items": { "type": "string" }, "default": [] }
      }
    }
  }
}
```

(Ollama’s `/api/chat` & `/api/generate`, `keep_alive`, `format: "json"`, and the `options`/sampling list come straight from the official API & Modelfile parameter docs.) ([Ollama][4])

---

# 3) Per-chat controls (sliders/toggles) — one JSON to drive your UI

This spec tells your UI what to render and how to map a control into request payloads for each backend. If a field isn’t supported by the chosen provider, just omit it from the request.

```json
{
  "type": "chat_controls",
  "controls": [
    {
      "id": "system_or_instructions",
      "label": "System / Instructions",
      "type": "multiline",
      "default": "",
      "description": "System prompt for Chat Completions; 'instructions' for Responses API.",
      "maps_to": {
        "openai_chat_completions": { "path": ["messages[*]"], "note": "Add as {role:'system', content:...} at the top" },
        "openai_responses": { "path": ["instructions"] },
        "ollama": { "path": ["messages[*]"], "note": "Add {role:'system', content:...} to messages" }
      }
    },
    {
      "id": "temperature",
      "label": "Temperature",
      "type": "slider",
      "min": 0.0,
      "max": 2.0,
      "step": 0.1,
      "default": 0.7,
      "description": "Higher = more diverse/creative; lower = more deterministic.",
      "supported_by": ["openai_chat_completions", "openai_responses", "ollama"],
      "maps_to": {
        "openai_chat_completions": { "path": ["temperature"] },
        "openai_responses": { "path": ["temperature"] },
        "ollama": { "path": ["options", "temperature"] }
      },
      "notes": "Unsupported for OpenAI reasoning models (o-series, gpt-5 reasoning modes). Omit when using those models."
    },
    {
      "id": "top_p",
      "label": "Top-p",
      "type": "slider",
      "min": 0.0,
      "max": 1.0,
      "step": 0.01,
      "default": 1.0,
      "supported_by": ["openai_chat_completions", "openai_responses", "ollama"],
      "maps_to": {
        "openai_chat_completions": { "path": ["top_p"] },
        "openai_responses": { "path": ["top_p"] },
        "ollama": { "path": ["options", "top_p"] }
      },
      "notes": "Unsupported for OpenAI reasoning models; omit there."
    },
    {
      "id": "max_tokens",
      "label": "Max output tokens",
      "type": "slider",
      "min": 1,
      "max": 8192,
      "step": 1,
      "default": 1024,
      "description": "Upper bound on tokens the model may generate.",
      "maps_to": {
        "openai_chat_completions": { "path": ["max_tokens"] },
        "openai_responses": { "path": ["max_output_tokens"] },
        "openai_reasoning_chat": { "path": ["max_completion_tokens"] },
        "ollama": { "path": ["options", "num_predict"] }
      }
    },
    {
      "id": "presence_penalty",
      "label": "Presence penalty",
      "type": "slider",
      "min": -2.0,
      "max": 2.0,
      "step": 0.1,
      "default": 0.0,
      "description": "Penalize introducing tokens simply because they already appeared.",
      "supported_by": ["openai_chat_completions", "openai_responses"],
      "maps_to": {
        "openai_chat_completions": { "path": ["presence_penalty"] },
        "openai_responses": { "path": ["presence_penalty"] }
      },
      "notes": "Not supported for OpenAI reasoning models; omit there."
    },
    {
      "id": "frequency_penalty",
      "label": "Frequency penalty",
      "type": "slider",
      "min": -2.0,
      "max": 2.0,
      "step": 0.1,
      "default": 0.0,
      "description": "Penalize token repetition frequency.",
      "supported_by": ["openai_chat_completions", "openai_responses"],
      "maps_to": {
        "openai_chat_completions": { "path": ["frequency_penalty"] },
        "openai_responses": { "path": ["frequency_penalty"] }
      },
      "notes": "Not supported for OpenAI reasoning models; omit there."
    },
    {
      "id": "seed",
      "label": "Seed",
      "type": "number",
      "default": null,
      "description": "When supported, fixes sampling randomness for reproducibility.",
      "supported_by": ["openai_chat_completions", "openai_responses", "ollama"],
      "maps_to": {
        "openai_chat_completions": { "path": ["seed"] },
        "openai_responses": { "path": ["seed"] },
        "ollama": { "path": ["options", "seed"] }
      }
    },
    {
      "id": "stop",
      "label": "Stop sequences",
      "type": "string_array",
      "default": [],
      "description": "Strings that will stop generation when encountered.",
      "supported_by": ["openai_chat_completions", "openai_responses", "ollama"],
      "maps_to": {
        "openai_chat_completions": { "path": ["stop"] },
        "openai_responses": { "path": ["stop"] },
        "ollama": { "path": ["options", "stop"] }
      }
    },
    {
      "id": "json_mode",
      "label": "Structured / JSON output",
      "type": "select",
      "values": ["off", "json_object", "json_schema"],
      "default": "off",
      "description": "Guarantee valid JSON (and optionally a JSON Schema).",
      "maps_to": {
        "openai_chat_completions": {
          "path": ["response_format"],
          "transform": "json_object => {\"type\":\"json_object\"}; json_schema => {\"type\":\"json_schema\",\"json_schema\":{\"name\":\"app_schema\",\"schema\":${schema},\"strict\":true}}; off => null"
        },
        "openai_responses": {
          "path": ["response_format"],
          "transform": "same as above; also set strict=true when using schema"
        },
        "ollama": {
          "path": ["format"],
          "transform": "json_object or json_schema => \"json\"; off => null",
          "note": "Also instruct model in the prompt to respond with JSON."
        }
      }
    },
    {
      "id": "tools",
      "label": "Tools / Function calling",
      "type": "tools_definition_array",
      "default": [],
      "description": "OpenAI-style functions/tools. Auto-routed by the model when allowed.",
      "maps_to": {
        "openai_chat_completions": { "path": ["tools"] },
        "openai_responses": { "path": ["tools"] },
        "ollama": { "path": ["tools"], "note": "Supported when stream=false per docs." }
      }
    },
    {
      "id": "tool_choice",
      "label": "Tool choice",
      "type": "select",
      "values": ["auto", "none", "required", "by_name"],
      "default": "auto",
      "maps_to": {
        "openai_chat_completions": { "path": ["tool_choice"] },
        "openai_responses": { "path": ["tool_choice"] }
      }
    },
    {
      "id": "stream",
      "label": "Stream responses",
      "type": "boolean",
      "default": true,
      "maps_to": {
        "openai_chat_completions": { "path": ["stream"] },
        "openai_responses": { "path": ["stream"] },
        "ollama": { "path": ["stream"] }
      }
    },

    /* ---- Ollama-only knobs ---- */
    {
      "id": "ollama_top_k",
      "label": "Top-k",
      "type": "slider",
      "min": 1,
      "max": 200,
      "step": 1,
      "default": 40,
      "supported_by": ["ollama"],
      "maps_to": { "ollama": { "path": ["options", "top_k"] } }
    },
    {
      "id": "ollama_repeat_penalty",
      "label": "Repetition penalty",
      "type": "slider",
      "min": 0.5,
      "max": 2.0,
      "step": 0.05,
      "default": 1.1,
      "supported_by": ["ollama"],
      "maps_to": { "ollama": { "path": ["options", "repeat_penalty"] } }
    },
    {
      "id": "ollama_mirostat",
      "label": "Mirostat mode",
      "type": "select",
      "values": [0, 1, 2],
      "default": 0,
      "supported_by": ["ollama"],
      "maps_to": { "ollama": { "path": ["options", "mirostat"] } }
    },

    /* ---- Reasoning-model-specific knobs (OpenAI) ---- */
    {
      "id": "reasoning_effort",
      "label": "Reasoning effort",
      "type": "select",
      "values": ["minimal", "low", "medium", "high"],
      "default": "low",
      "supported_by": ["openai_responses", "openai_chat_completions"],
      "applies_to_models": ["o1*", "o3*", "o4-mini*", "gpt-5*"],
      "maps_to": {
        "openai_responses": { "path": ["reasoning", "effort"] },
        "openai_chat_completions": { "path": ["reasoning_effort"] }
      },
      "notes": "When using reasoning models, many sampling params (temperature, top_p, penalties) are unsupported—omit them."
    },
    {
      "id": "verbosity",
      "label": "Verbosity",
      "type": "select",
      "values": ["low", "medium", "high"],
      "default": "medium",
      "applies_to_models": ["gpt-5*"],
      "supported_by": ["openai_responses", "openai_chat_completions"],
      "maps_to": {
        "openai_responses": { "path": ["verbosity"] },
        "openai_chat_completions": { "path": ["verbosity"] }
      }
    }
  ]
}
```

References: Responses API (+ reasoning/tooling/structured outputs), Chat Completions, and what’s unsupported for reasoning models. ([GitHub][1], [OpenAI Cookbook][5], [OpenAI Platform][6], [Microsoft Learn][3])

---

# 4) Request body templates

Use these to compose the final payloads by applying the mappings above.

### 4.1 OpenAI **Responses** API (recommended default)

```json
{
  "method": "POST",
  "url": "{base_url}/v1/responses",
  "headers": {
    "Authorization": "Bearer {api_key}",
    "OpenAI-Organization": "{organization?}",
    "OpenAI-Project": "{project?}",
    "Content-Type": "application/json"
  },
  "body": {
    "model": "{default_model}",
    "input": "{user_text_or_blocks}",
    "instructions": "{system_or_instructions?}",
    "max_output_tokens": ${max_tokens?},
    "temperature": ${temperature?},
    "top_p": ${top_p?},
    "stop": ${stop?},
    "seed": ${seed?},
    "tools": ${tools?},
    "tool_choice": "${tool_choice?}",
    "response_format": ${response_format_or_null},
    "stream": ${stream},
    "reasoning": { "effort": "${reasoning_effort?}" }
  }
}
```

Notes:

* For **structured outputs**, set `response_format` to `{"type":"json_object"}` or a JSON Schema variant with `strict: true`. ([OpenAI Platform][6])
* Reasoning models work here but disable temp/top\_p/penalties and prefer `reasoning.effort` + `max_output_tokens`. ([Microsoft Learn][3])
* Responses accepts `input` as a string or message blocks; both are supported in official clients. ([GitHub][1])

---

### 4.2 OpenAI **Chat Completions** API (fallback / compatibility)

```json
{
  "method": "POST",
  "url": "{base_url}/v1/chat/completions",
  "headers": {
    "Authorization": "Bearer {api_key}",
    "OpenAI-Organization": "{organization?}",
    "OpenAI-Project": "{project?}",
    "Content-Type": "application/json"
  },
  "body": {
    "model": "{default_model}",
    "messages": [
      { "role": "system", "content": "{system_or_instructions?}" },
      { "role": "user", "content": "{user_text}" }
    ],
    "temperature": ${temperature?},
    "top_p": ${top_p?},
    "max_tokens": ${max_tokens?},
    "presence_penalty": ${presence_penalty?},
    "frequency_penalty": ${frequency_penalty?},
    "stop": ${stop?},
    "seed": ${seed?},
    "tools": ${tools?},
    "tool_choice": "${tool_choice?}",
    "response_format": ${response_format_or_null},
    "stream": ${stream}
  }
}
```

Notes:

* If targeting **reasoning** models via Chat Completions, use `max_completion_tokens` and omit temp/top\_p/penalties. ([Microsoft Learn][3])
* Many OpenAI-compatible providers still prefer this endpoint and support the core fields above. ([OpenAI Platform][2])

---

### 4.3 **Azure OpenAI** route shape (when `api_type = "azure"`)

For **Responses**:

```
POST {base_url}/openai/deployments/{deployment}/responses?api-version={api_version}
```

For **Chat Completions**:

```
POST {base_url}/openai/deployments/{deployment}/chat/completions?api-version={api_version}
```

…and use the same bodies as above. ([Microsoft Learn][3])

---

### 4.4 **Ollama** (chat)

```json
{
  "method": "POST",
  "url": "{host}/api/chat",
  "headers": { "Content-Type": "application/json" },
  "body": {
    "model": "{model}",
    "messages": [
      { "role": "system", "content": "{system_or_instructions?}" },
      { "role": "user", "content": "{user_text}" }
    ],
    "tools": ${tools_or_omit_if_streaming}, 
    "stream": ${stream},
    "keep_alive": "{keep_alive}",
    "format": ${ollama_format_json_or_null},
    "options": {
      "temperature": ${temperature?},
      "top_p": ${top_p?},
      "top_k": ${ollama_top_k?},
      "min_p": ${min_p?},
      "num_predict": ${max_tokens?},
      "num_ctx": ${num_ctx?},
      "seed": ${seed?},
      "repeat_penalty": ${ollama_repeat_penalty?},
      "repeat_last_n": ${repeat_last_n?},
      "tfs_z": ${tfs_z?},
      "mirostat": ${ollama_mirostat?},
      "mirostat_tau": ${mirostat_tau?},
      "mirostat_eta": ${mirostat_eta?},
      "stop": ${stop?}
    }
  }
}
```

Notes:

* `tools` require `stream: false` per docs; otherwise omit.
* For single-prompt use, swap to `POST {host}/api/generate` with `prompt` instead of `messages`. ([Ollama][4])

---

## Practical compatibility rules (TL;DR)

* Prefer **Responses** for OpenAI-compatible providers; fall back to **Chat Completions** when needed. ([GitHub][1])
* If the selected model is an **OpenAI reasoning** model (o-series, some GPT-5 modes):

  * send `reasoning_effort` (and optionally `verbosity`),
  * use `max_output_tokens` (Responses) or `max_completion_tokens` (Chat Completions),
  * **omit** `temperature`, `top_p`, `presence_penalty`, `frequency_penalty`, `logprobs`, `logit_bias`. ([Microsoft Learn][3])
* For **structured output**, set `response_format` (JSON object or JSON Schema with `strict: true`), or for Ollama set `format: "json"` and also instruct the model in the prompt. ([OpenAI Platform][6], [Ollama][4])
* For **Ollama**, all sampling knobs go under `options` and you can keep the model warm with `keep_alive`. ([Ollama][4])

---

If you’d like, I can also spit out tiny TypeScript zod schemas for these, or wire up a minimal adapter that takes the **chat\_controls** JSON and compiles the correct provider payload automatically.

[1]: https://github.com/openai/openai-python?utm_source=chatgpt.com "The official Python library for the OpenAI API"
[2]: https://platform.openai.com/docs/api-reference/chat?utm_source=chatgpt.com "API Reference - OpenAI API"
[3]: https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/reasoning "Azure OpenAI reasoning models - GPT-5 series, o3-mini, o1, o1-mini - Azure OpenAI | Microsoft Learn"
[4]: https://ollama.readthedocs.io/en/api/ "API Reference - Ollama English Documentation"
[5]: https://cookbook.openai.com/examples/responses_api/reasoning_items?utm_source=chatgpt.com "Better performance from reasoning models using the ..."
[6]: https://platform.openai.com/docs/guides/structured-outputs?utm_source=chatgpt.com "Structured model outputs - OpenAI API"
