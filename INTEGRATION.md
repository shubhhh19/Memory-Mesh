# Integration Guide

This guide provides detailed examples for integrating Memory Mesh into your application using various programming languages and frameworks.

## Table of Contents

- [Python](#python)
- [JavaScript/TypeScript](#javascripttypescript)
- [Go](#go)
- [Authentication](#authentication)
- [Error Handling](#error-handling)
- [Best Practices](#best-practices)

## Python

### Basic Setup

```python
import httpx
from typing import Optional, List, Dict, Any

class MemoryMeshClient:
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        access_token: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Content-Type": "application/json",
                **({"Authorization": f"Bearer {access_token}"} if access_token else {}),
                **({"x-api-key": api_key} if api_key else {}),
            },
            timeout=30.0
        )
    
    async def close(self):
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
```

### Authentication

```python
# Register a new user
async def register_user(
    client: httpx.AsyncClient,
    email: str,
    username: str,
    password: str
) -> Dict[str, Any]:
    response = await client.post(
        "/v1/auth/register",
        json={
            "email": email,
            "username": username,
            "password": password
        }
    )
    response.raise_for_status()
    return response.json()

# Login
async def login(
    client: httpx.AsyncClient,
    email: str,
    password: str
) -> Dict[str, Any]:
    response = await client.post(
        "/v1/auth/login",
        json={
            "email": email,
            "password": password
        }
    )
    response.raise_for_status()
    return response.json()

# Usage
async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
    # Register
    user_data = await register_user(client, "user@example.com", "testuser", "SecurePass123")
    
    # Login
    auth_data = await login(client, "user@example.com", "SecurePass123")
    access_token = auth_data["access_token"]
    refresh_token = auth_data["refresh_token"]
```

### Storing Messages

```python
async def store_message(
    client: MemoryMeshClient,
    tenant_id: str,
    conversation_id: str,
    role: str,
    content: str,
    importance: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    response = await client.client.post(
        "/v1/messages",
        json={
            "tenant_id": tenant_id,
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "importance": importance,
            "metadata": metadata
        }
    )
    response.raise_for_status()
    return response.json()

# Usage
async with MemoryMeshClient(
    base_url="http://localhost:8000",
    access_token="your-access-token"
) as client:
    message = await store_message(
        client,
        tenant_id="my-app",
        conversation_id="user-123",
        role="user",
        content="I need help with Python programming",
        importance=0.8,
        metadata={"source": "web", "session_id": "abc123"}
    )
    print(f"Stored message with ID: {message['id']}")
```

### Batch Operations

```python
async def batch_create_messages(
    client: MemoryMeshClient,
    messages: List[Dict[str, Any]]
) -> Dict[str, Any]:
    response = await client.client.post(
        "/v1/messages/batch",
        json={"messages": messages}
    )
    response.raise_for_status()
    return response.json()

# Usage
messages = [
    {
        "tenant_id": "my-app",
        "conversation_id": "user-123",
        "role": "user",
        "content": "Hello, how are you?"
    },
    {
        "tenant_id": "my-app",
        "conversation_id": "user-123",
        "role": "assistant",
        "content": "I'm doing well, thank you!"
    }
]

result = await batch_create_messages(client, messages)
print(f"Created {len(result['created'])} messages")
```

### Semantic Search

```python
async def search_messages(
    client: MemoryMeshClient,
    tenant_id: str,
    query: str,
    top_k: int = 5,
    conversation_id: Optional[str] = None,
    min_importance: Optional[float] = None
) -> List[Dict[str, Any]]:
    params = {
        "tenant_id": tenant_id,
        "query": query,
        "top_k": top_k
    }
    if conversation_id:
        params["conversation_id"] = conversation_id
    if min_importance:
        params["min_importance"] = min_importance
    
    response = await client.client.get("/v1/memory/search", params=params)
    response.raise_for_status()
    return response.json()["results"]

# Usage
results = await search_messages(
    client,
    tenant_id="my-app",
    query="Python programming help",
    top_k=10
)

for result in results:
    print(f"Score: {result['score']:.3f}")
    print(f"Content: {result['content']}")
    print(f"Role: {result['role']}")
    print("---")
```

### Conversation Management

```python
async def create_conversation(
    client: MemoryMeshClient,
    tenant_id: str,
    conversation_id: str,
    title: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    response = await client.client.post(
        "/v1/conversations",
        json={
            "tenant_id": tenant_id,
            "conversation_id": conversation_id,
            "title": title,
            "metadata": metadata
        }
    )
    response.raise_for_status()
    return response.json()

async def get_conversation(
    client: MemoryMeshClient,
    conversation_id: str
) -> Dict[str, Any]:
    response = await client.client.get(f"/v1/conversations/{conversation_id}")
    response.raise_for_status()
    return response.json()

async def list_conversations(
    client: MemoryMeshClient,
    tenant_id: str,
    limit: int = 20,
    offset: int = 0
) -> Dict[str, Any]:
    response = await client.client.get(
        "/v1/conversations",
        params={"tenant_id": tenant_id, "limit": limit, "offset": offset}
    )
    response.raise_for_status()
    return response.json()
```

## JavaScript/TypeScript

### Basic Setup

```typescript
interface MemoryMeshClientOptions {
  baseUrl: string;
  accessToken?: string;
  apiKey?: string;
}

class MemoryMeshClient {
  private baseUrl: string;
  private headers: Record<string, string>;

  constructor(options: MemoryMeshClientOptions) {
    this.baseUrl = options.baseUrl.replace(/\/$/, '');
    this.headers = {
      'Content-Type': 'application/json',
      ...(options.accessToken && { Authorization: `Bearer ${options.accessToken}` }),
      ...(options.apiKey && { 'x-api-key': options.apiKey }),
    };
  }

  private async request<T>(
    method: string,
    path: string,
    body?: any,
    params?: Record<string, any>
  ): Promise<T> {
    const url = new URL(`${this.baseUrl}${path}`);
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        url.searchParams.append(key, String(value));
      });
    }

    const response = await fetch(url.toString(), {
      method,
      headers: this.headers,
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: response.statusText }));
      throw new Error(error.message || `HTTP ${response.status}`);
    }

    return response.json();
  }
}
```

### Authentication

```typescript
// Register
async function registerUser(
  client: MemoryMeshClient,
  email: string,
  username: string,
  password: string
): Promise<any> {
  return client.request('POST', '/v1/auth/register', {
    email,
    username,
    password,
  });
}

// Login
async function login(
  client: MemoryMeshClient,
  email: string,
  password: string
): Promise<{ access_token: string; refresh_token: string }> {
  return client.request('POST', '/v1/auth/login', {
    email,
    password,
  });
}

// Usage
const client = new MemoryMeshClient({ baseUrl: 'http://localhost:8000' });
const authData = await login(client, 'user@example.com', 'SecurePass123');
const authenticatedClient = new MemoryMeshClient({
  baseUrl: 'http://localhost:8000',
  accessToken: authData.access_token,
});
```

### Storing Messages

```typescript
interface MessageInput {
  tenant_id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  importance?: number;
  metadata?: Record<string, any>;
}

async function storeMessage(
  client: MemoryMeshClient,
  message: MessageInput
): Promise<any> {
  return client.request('POST', '/v1/messages', message);
}

// Usage
const message = await storeMessage(authenticatedClient, {
  tenant_id: 'my-app',
  conversation_id: 'user-123',
  role: 'user',
  content: 'I need help with TypeScript',
  importance: 0.8,
  metadata: { source: 'web' },
});
```

### Semantic Search

```typescript
interface SearchOptions {
  tenant_id: string;
  query: string;
  top_k?: number;
  conversation_id?: string;
  min_importance?: number;
}

async function searchMessages(
  client: MemoryMeshClient,
  options: SearchOptions
): Promise<Array<{ id: string; content: string; score: number; role: string }>> {
  const result = await client.request<{ results: any[] }>(
    'GET',
    '/v1/memory/search',
    undefined,
    options
  );
  return result.results;
}

// Usage
const results = await searchMessages(authenticatedClient, {
  tenant_id: 'my-app',
  query: 'TypeScript help',
  top_k: 10,
});

results.forEach((result) => {
  console.log(`Score: ${result.score.toFixed(3)}`);
  console.log(`Content: ${result.content}`);
});
```

### React Hook Example

```typescript
import { useState, useEffect } from 'react';

function useMemoryMesh(baseUrl: string, accessToken?: string) {
  const [client] = useState(() => new MemoryMeshClient({ baseUrl, accessToken }));

  const search = async (tenantId: string, query: string, topK = 5) => {
    return searchMessages(client, {
      tenant_id: tenantId,
      query,
      top_k: topK,
    });
  };

  const store = async (message: MessageInput) => {
    return storeMessage(client, message);
  };

  return { search, store };
}

// Usage in component
function SearchComponent() {
  const { search, store } = useMemoryMesh('http://localhost:8000', 'token');
  const [results, setResults] = useState([]);

  const handleSearch = async (query: string) => {
    const searchResults = await search('my-app', query);
    setResults(searchResults);
  };

  return (
    <div>
      <input onKeyPress={(e) => e.key === 'Enter' && handleSearch(e.target.value)} />
      {results.map((r) => (
        <div key={r.id}>{r.content}</div>
      ))}
    </div>
  );
}
```

## Go

### Basic Setup

```go
package main

import (
    "bytes"
    "encoding/json"
    "fmt"
    "io"
    "net/http"
    "time"
)

type MemoryMeshClient struct {
    BaseURL     string
    AccessToken string
    APIKey      string
    HTTPClient  *http.Client
}

func NewMemoryMeshClient(baseURL, accessToken, apiKey string) *MemoryMeshClient {
    return &MemoryMeshClient{
        BaseURL:     baseURL,
        AccessToken: accessToken,
        APIKey:      apiKey,
        HTTPClient: &http.Client{
            Timeout: 30 * time.Second,
        },
    }
}

func (c *MemoryMeshClient) request(method, path string, body interface{}) ([]byte, error) {
    var reqBody io.Reader
    if body != nil {
        jsonData, err := json.Marshal(body)
        if err != nil {
            return nil, err
        }
        reqBody = bytes.NewBuffer(jsonData)
    }

    req, err := http.NewRequest(method, c.BaseURL+path, reqBody)
    if err != nil {
        return nil, err
    }

    req.Header.Set("Content-Type", "application/json")
    if c.AccessToken != "" {
        req.Header.Set("Authorization", "Bearer "+c.AccessToken)
    }
    if c.APIKey != "" {
        req.Header.Set("x-api-key", c.APIKey)
    }

    resp, err := c.HTTPClient.Do(req)
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()

    if resp.StatusCode >= 400 {
        return nil, fmt.Errorf("HTTP %d: %s", resp.StatusCode, resp.Status)
    }

    return io.ReadAll(resp.Body)
}
```

### Storing Messages

```go
type Message struct {
    TenantID       string                 `json:"tenant_id"`
    ConversationID string                 `json:"conversation_id"`
    Role          string                 `json:"role"`
    Content       string                 `json:"content"`
    Importance    *float64               `json:"importance,omitempty"`
    Metadata      map[string]interface{} `json:"metadata,omitempty"`
}

func (c *MemoryMeshClient) StoreMessage(msg Message) (map[string]interface{}, error) {
    data, err := c.request("POST", "/v1/messages", msg)
    if err != nil {
        return nil, err
    }

    var result map[string]interface{}
    if err := json.Unmarshal(data, &result); err != nil {
        return nil, err
    }
    return result, nil
}

// Usage
client := NewMemoryMeshClient("http://localhost:8000", "your-token", "")
message := Message{
    TenantID:       "my-app",
    ConversationID: "user-123",
    Role:          "user",
    Content:       "I need help with Go programming",
}
result, err := client.StoreMessage(message)
if err != nil {
    log.Fatal(err)
}
fmt.Printf("Stored message: %v\n", result)
```

### Semantic Search

```go
type SearchParams struct {
    TenantID       string  `json:"tenant_id"`
    Query         string  `json:"query"`
    TopK          int     `json:"top_k,omitempty"`
    ConversationID string `json:"conversation_id,omitempty"`
    MinImportance *float64 `json:"min_importance,omitempty"`
}

type SearchResult struct {
    Results []struct {
        ID       string  `json:"id"`
        Content  string  `json:"content"`
        Score    float64 `json:"score"`
        Role     string  `json:"role"`
    } `json:"results"`
}

func (c *MemoryMeshClient) Search(params SearchParams) (*SearchResult, error) {
    query := fmt.Sprintf(
        "tenant_id=%s&query=%s&top_k=%d",
        params.TenantID,
        params.Query,
        params.TopK,
    )
    if params.ConversationID != "" {
        query += "&conversation_id=" + params.ConversationID
    }

    data, err := c.request("GET", "/v1/memory/search?"+query, nil)
    if err != nil {
        return nil, err
    }

    var result SearchResult
    if err := json.Unmarshal(data, &result); err != nil {
        return nil, err
    }
    return &result, nil
}

// Usage
results, err := client.Search(SearchParams{
    TenantID: "my-app",
    Query:   "Go programming help",
    TopK:    10,
})
if err != nil {
    log.Fatal(err)
}

for _, result := range results.Results {
    fmt.Printf("Score: %.3f - %s\n", result.Score, result.Content)
}
```

## Authentication

### Token Refresh

```python
async def refresh_token(
    client: httpx.AsyncClient,
    refresh_token: str
) -> Dict[str, Any]:
    response = await client.post(
        "/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    response.raise_for_status()
    return response.json()
```

### API Key Authentication

```python
# Create API key (requires authentication)
async def create_api_key(
    client: MemoryMeshClient,
    name: str,
    expires_days: Optional[int] = None
) -> Dict[str, Any]:
    response = await client.client.post(
        "/v1/auth/api-keys",
        json={"name": name, "expires_days": expires_days}
    )
    response.raise_for_status()
    return response.json()

# Use API key
client = MemoryMeshClient(
    base_url="http://localhost:8000",
    api_key="your-api-key-here"
)
```

## Error Handling

### Python

```python
import httpx

async def store_message_safe(client: MemoryMeshClient, message: Dict[str, Any]):
    try:
        return await store_message(client, message)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            # Token expired, refresh and retry
            print("Token expired, please refresh")
        elif e.response.status_code == 429:
            # Rate limited
            retry_after = e.response.headers.get("Retry-After", "60")
            print(f"Rate limited, retry after {retry_after} seconds")
        else:
            print(f"Error: {e.response.status_code} - {e.response.text}")
        raise
    except httpx.RequestError as e:
        print(f"Network error: {e}")
        raise
```

### JavaScript/TypeScript

```typescript
async function storeMessageSafe(
  client: MemoryMeshClient,
  message: MessageInput
): Promise<any> {
  try {
    return await storeMessage(client, message);
  } catch (error: any) {
    if (error.message.includes('401')) {
      console.error('Authentication failed, please refresh token');
    } else if (error.message.includes('429')) {
      console.error('Rate limited, please retry later');
    } else {
      console.error('Error storing message:', error);
    }
    throw error;
  }
}
```

## Best Practices

### 1. Connection Pooling

```python
# Reuse client instances
client = MemoryMeshClient(
    base_url="http://localhost:8000",
    access_token=access_token
)

# Use async context manager
async with client:
    # Multiple operations
    await store_message(client, ...)
    await search_messages(client, ...)
```

### 2. Retry Logic

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def store_message_with_retry(client: MemoryMeshClient, message: Dict[str, Any]):
    return await store_message(client, message)
```

### 3. Batch Operations

Always use batch endpoints when storing multiple messages:

```python
# Good: Batch operation
messages = [message1, message2, message3]
await batch_create_messages(client, messages)

# Avoid: Multiple individual requests
for message in messages:
    await store_message(client, message)  # Slower
```

### 4. Caching

Cache search results when appropriate:

```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=100)
async def cached_search(client: MemoryMeshClient, tenant_id: str, query: str):
    return await search_messages(client, tenant_id, query, top_k=5)
```

### 5. Error Handling

Always handle errors gracefully:

```python
try:
    result = await store_message(client, message)
except httpx.HTTPStatusError as e:
    if e.response.status_code == 400:
        # Validation error
        errors = e.response.json()
        print(f"Validation errors: {errors}")
    elif e.response.status_code == 401:
        # Authentication error
        print("Please authenticate")
    else:
        print(f"Unexpected error: {e}")
```

### 6. Type Safety

Use type hints and Pydantic models:

```python
from pydantic import BaseModel

class MessageInput(BaseModel):
    tenant_id: str
    conversation_id: str
    role: str
    content: str
    importance: float | None = None
    metadata: dict[str, Any] | None = None

message = MessageInput(
    tenant_id="my-app",
    conversation_id="user-123",
    role="user",
    content="Hello"
)
```

## WebSocket Integration

### Real-time Updates

```python
import asyncio
import websockets
import json

async def listen_for_updates(tenant_id: str, access_token: str):
    uri = f"ws://localhost:8000/ws/messages/{tenant_id}"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    async with websockets.connect(uri, extra_headers=headers) as websocket:
        async for message in websocket:
            data = json.loads(message)
            print(f"New message: {data}")

# Usage
asyncio.run(listen_for_updates("my-app", "your-token"))
```

## Next Steps

- Check the [API Reference](http://localhost:8000/docs) for complete endpoint documentation
- See [README.md](README.md) for more examples
- Review [README_PRODUCTION.md](README_PRODUCTION.md) for production deployment guidance

