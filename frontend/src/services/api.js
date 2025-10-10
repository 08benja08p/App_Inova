const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

async function handleResponse(response) {
  if (!response.ok) {
    const detail = await safeParseJSON(response);
    const message = detail?.detail ?? response.statusText;
    throw new Error(`Error ${response.status}: ${message}`);
  }
  return response.status === 204 ? null : response.json();
}

async function safeParseJSON(response) {
  try {
    return await response.clone().json();
  } catch (error) {
    return null;
  }
}

export async function uploadDocument(file, { docType, languageHint } = {}) {
  const formData = new FormData();
  formData.append('file', file);
  if (docType) {
    formData.append('doc_type', docType);
  }
  if (languageHint) {
    formData.append('language_hint', languageHint);
  }
  const response = await fetch(`${API_BASE_URL}/documents`, {
    method: 'POST',
    body: formData,
  });
  return handleResponse(response);
}

export async function getDocumentDetail(docId) {
  const response = await fetch(`${API_BASE_URL}/documents/${docId}`);
  return handleResponse(response);
}

export async function getDocumentEntities(docId) {
  const response = await fetch(`${API_BASE_URL}/documents/${docId}/entities`);
  return handleResponse(response);
}

export async function getDocumentKeywords(docId) {
  const response = await fetch(`${API_BASE_URL}/documents/${docId}/keywords`);
  return handleResponse(response);
}

export async function getDocumentText(docId) {
  const response = await fetch(`${API_BASE_URL}/documents/${docId}/text`);
  return handleResponse(response);
}
