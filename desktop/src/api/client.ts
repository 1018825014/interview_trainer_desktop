import { SessionBootstrapPayload, TranscriptPayload } from "../types";

interface JsonRequestOptions {
  method?: string;
  payload?: unknown;
  errorMessage: string;
}

export async function requestJson<T>(url: string, options: JsonRequestOptions): Promise<T> {
  const init: RequestInit = {
    method: options.method ?? "GET",
  };
  if (options.payload !== undefined) {
    init.headers = { "Content-Type": "application/json" };
    init.body = JSON.stringify(options.payload);
  }
  const response = await fetch(url, init);
  if (!response.ok) {
    throw new Error(options.errorMessage);
  }
  return (await response.json()) as T;
}

export async function pingBackend(baseUrl: string): Promise<boolean> {
  try {
    const response = await fetch(`${baseUrl}/health`);
    return response.ok;
  } catch {
    return false;
  }
}

export async function fetchAudioRecommendation(baseUrl: string) {
  return requestJson(`${baseUrl}/api/audio/recommendation`, {
    errorMessage: "Failed to load audio recommendation",
  });
}

export async function fetchAudioCapabilities(baseUrl: string) {
  return requestJson(`${baseUrl}/api/audio/capabilities`, {
    errorMessage: "Failed to load audio capabilities",
  });
}

export async function createAudioSession(baseUrl: string, payload: Record<string, unknown>) {
  return requestJson(`${baseUrl}/api/audio/sessions`, {
    method: "POST",
    payload,
    errorMessage: "Failed to create audio session",
  });
}

export async function startAudioSession(baseUrl: string, audioSessionId: string) {
  return requestJson(`${baseUrl}/api/audio/sessions/${audioSessionId}/start`, {
    method: "POST",
    payload: {},
    errorMessage: "Failed to start audio session",
  });
}

export async function pushAudioFrame(
  baseUrl: string,
  audioSessionId: string,
  payload: Record<string, unknown>,
) {
  return requestJson(`${baseUrl}/api/audio/sessions/${audioSessionId}/frames`, {
    method: "POST",
    payload,
    errorMessage: "Failed to push audio frame",
  });
}

export async function transcribeAudioSession(
  baseUrl: string,
  audioSessionId: string,
  payload: Record<string, unknown>,
) {
  return requestJson(`${baseUrl}/api/audio/sessions/${audioSessionId}/transcribe`, {
    method: "POST",
    payload,
    errorMessage: "Failed to transcribe audio session",
  });
}

export async function createLiveBridge(baseUrl: string, payload: Record<string, unknown>) {
  return requestJson(`${baseUrl}/api/audio/live-bridges`, {
    method: "POST",
    payload,
    errorMessage: "Failed to create live bridge",
  });
}

export async function getLiveBridge(baseUrl: string, bridgeId: string) {
  return requestJson(`${baseUrl}/api/audio/live-bridges/${bridgeId}`, {
    errorMessage: "Failed to load live bridge",
  });
}

export async function stopLiveBridge(baseUrl: string, bridgeId: string) {
  return requestJson(`${baseUrl}/api/audio/live-bridges/${bridgeId}/stop`, {
    method: "POST",
    payload: {},
    errorMessage: "Failed to stop live bridge",
  });
}

export async function createSession(baseUrl: string, payload: SessionBootstrapPayload) {
  return requestJson(`${baseUrl}/api/sessions`, {
    method: "POST",
    payload,
    errorMessage: "Failed to create session",
  });
}

export async function listWorkspaces(baseUrl: string) {
  return requestJson(`${baseUrl}/api/workspaces`, {
    errorMessage: "Failed to load workspaces",
  });
}

export async function createWorkspace(baseUrl: string, payload: Record<string, unknown>) {
  return requestJson(`${baseUrl}/api/workspaces`, {
    method: "POST",
    payload,
    errorMessage: "Failed to create workspace",
  });
}

export async function getWorkspace(baseUrl: string, workspaceId: string) {
  return requestJson(`${baseUrl}/api/workspaces/${workspaceId}`, {
    errorMessage: "Failed to load workspace",
  });
}

export async function updateWorkspace(
  baseUrl: string,
  workspaceId: string,
  payload: Record<string, unknown>,
) {
  return requestJson(`${baseUrl}/api/workspaces/${workspaceId}`, {
    method: "PUT",
    payload,
    errorMessage: "Failed to update workspace",
  });
}

export async function compileWorkspace(baseUrl: string, workspaceId: string) {
  return requestJson(`${baseUrl}/api/workspaces/${workspaceId}/compile`, {
    method: "POST",
    payload: {},
    errorMessage: "Failed to compile workspace",
  });
}

export async function importWorkspacePath(
  baseUrl: string,
  workspaceId: string,
  payload: Record<string, unknown>,
) {
  return requestJson(`${baseUrl}/api/workspaces/${workspaceId}/import-path`, {
    method: "POST",
    payload,
    errorMessage: "Failed to import workspace path",
  });
}

export async function getAnswer(baseUrl: string, sessionId: string, turnId: string) {
  return requestJson(`${baseUrl}/api/sessions/${sessionId}/answers/${turnId}`, {
    errorMessage: "Failed to load answer",
  });
}

export async function sendTranscript(baseUrl: string, sessionId: string, payload: TranscriptPayload) {
  return requestJson(`${baseUrl}/api/sessions/${sessionId}/transcripts`, {
    method: "POST",
    payload,
    errorMessage: "Failed to send transcript",
  });
}

export async function tickSession(baseUrl: string, sessionId: string, nowTs: number) {
  return requestJson(`${baseUrl}/api/sessions/${sessionId}/tick`, {
    method: "POST",
    payload: { now_ts: nowTs },
    errorMessage: "Failed to tick session",
  });
}
