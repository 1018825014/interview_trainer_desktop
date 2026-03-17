import { SessionBootstrapPayload, TranscriptPayload } from "../types";

export async function pingBackend(baseUrl: string): Promise<boolean> {
  try {
    const response = await fetch(`${baseUrl}/health`);
    return response.ok;
  } catch {
    return false;
  }
}

export async function fetchAudioRecommendation(baseUrl: string) {
  const response = await fetch(`${baseUrl}/api/audio/recommendation`);
  if (!response.ok) {
    throw new Error("Failed to load audio recommendation");
  }
  return response.json();
}

export async function fetchAudioCapabilities(baseUrl: string) {
  const response = await fetch(`${baseUrl}/api/audio/capabilities`);
  if (!response.ok) {
    throw new Error("Failed to load audio capabilities");
  }
  return response.json();
}

export async function createAudioSession(baseUrl: string, payload: Record<string, unknown>) {
  const response = await fetch(`${baseUrl}/api/audio/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error("Failed to create audio session");
  }
  return response.json();
}

export async function startAudioSession(baseUrl: string, audioSessionId: string) {
  const response = await fetch(`${baseUrl}/api/audio/sessions/${audioSessionId}/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  if (!response.ok) {
    throw new Error("Failed to start audio session");
  }
  return response.json();
}

export async function pushAudioFrame(
  baseUrl: string,
  audioSessionId: string,
  payload: Record<string, unknown>,
) {
  const response = await fetch(`${baseUrl}/api/audio/sessions/${audioSessionId}/frames`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error("Failed to push audio frame");
  }
  return response.json();
}

export async function transcribeAudioSession(
  baseUrl: string,
  audioSessionId: string,
  payload: Record<string, unknown>,
) {
  const response = await fetch(`${baseUrl}/api/audio/sessions/${audioSessionId}/transcribe`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error("Failed to transcribe audio session");
  }
  return response.json();
}

export async function createLiveBridge(baseUrl: string, payload: Record<string, unknown>) {
  const response = await fetch(`${baseUrl}/api/audio/live-bridges`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error("Failed to create live bridge");
  }
  return response.json();
}

export async function getLiveBridge(baseUrl: string, bridgeId: string) {
  const response = await fetch(`${baseUrl}/api/audio/live-bridges/${bridgeId}`);
  if (!response.ok) {
    throw new Error("Failed to load live bridge");
  }
  return response.json();
}

export async function stopLiveBridge(baseUrl: string, bridgeId: string) {
  const response = await fetch(`${baseUrl}/api/audio/live-bridges/${bridgeId}/stop`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  if (!response.ok) {
    throw new Error("Failed to stop live bridge");
  }
  return response.json();
}

export async function createSession(baseUrl: string, payload: SessionBootstrapPayload) {
  const response = await fetch(`${baseUrl}/api/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error("Failed to create session");
  }
  return response.json();
}

export async function listWorkspaces(baseUrl: string) {
  const response = await fetch(`${baseUrl}/api/workspaces`);
  if (!response.ok) {
    throw new Error("Failed to load workspaces");
  }
  return response.json();
}

export async function createWorkspace(baseUrl: string, payload: Record<string, unknown>) {
  const response = await fetch(`${baseUrl}/api/workspaces`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error("Failed to create workspace");
  }
  return response.json();
}

export async function getWorkspace(baseUrl: string, workspaceId: string) {
  const response = await fetch(`${baseUrl}/api/workspaces/${workspaceId}`);
  if (!response.ok) {
    throw new Error("Failed to load workspace");
  }
  return response.json();
}

export async function updateWorkspace(
  baseUrl: string,
  workspaceId: string,
  payload: Record<string, unknown>,
) {
  const response = await fetch(`${baseUrl}/api/workspaces/${workspaceId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error("Failed to update workspace");
  }
  return response.json();
}

export async function compileWorkspace(baseUrl: string, workspaceId: string) {
  const response = await fetch(`${baseUrl}/api/workspaces/${workspaceId}/compile`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  if (!response.ok) {
    throw new Error("Failed to compile workspace");
  }
  return response.json();
}

export async function importWorkspacePath(
  baseUrl: string,
  workspaceId: string,
  payload: Record<string, unknown>,
) {
  const response = await fetch(`${baseUrl}/api/workspaces/${workspaceId}/import-path`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error("Failed to import workspace path");
  }
  return response.json();
}

export async function getAnswer(baseUrl: string, sessionId: string, turnId: string) {
  const response = await fetch(`${baseUrl}/api/sessions/${sessionId}/answers/${turnId}`);
  if (!response.ok) {
    throw new Error("Failed to load answer");
  }
  return response.json();
}

export async function sendTranscript(baseUrl: string, sessionId: string, payload: TranscriptPayload) {
  const response = await fetch(`${baseUrl}/api/sessions/${sessionId}/transcripts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error("Failed to send transcript");
  }
  return response.json();
}

export async function tickSession(baseUrl: string, sessionId: string, nowTs: number) {
  const response = await fetch(`${baseUrl}/api/sessions/${sessionId}/tick`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ now_ts: nowTs }),
  });
  if (!response.ok) {
    throw new Error("Failed to tick session");
  }
  return response.json();
}
