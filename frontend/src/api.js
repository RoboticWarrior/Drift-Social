const CLIENT_KEY = "drift.clientId";

export function getClientId() {
  try {
    let id = localStorage.getItem(CLIENT_KEY);
    if (!id) {
      id = `c-${crypto.randomUUID()}`;
      localStorage.setItem(CLIENT_KEY, id);
    }
    return id;
  } catch {
    return "c-anonymous";
  }
}

async function readJson(response) {
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const message = data?.error || `Request failed (${response.status})`;
    throw new Error(message);
  }
  return data;
}

export async function fetchPosts({ cursor = null, limit = 6 } = {}) {
  const params = new URLSearchParams({ limit: String(limit), client_id: getClientId() });
  if (cursor != null) params.set("before", String(cursor));
  const response = await fetch(`/api/posts?${params}`, { headers: { Accept: "application/json" } });
  return readJson(response);
}

export async function createPost({ text, authorName, files, onProgress }) {
  const form = new FormData();
  form.append("text", text);
  form.append("author_name", authorName);
  form.append("client_id", getClientId());
  for (const file of files) form.append("media", file);

  // XHR (rather than fetch) so the composer can show real upload progress.
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("POST", "/api/posts");
    request.responseType = "json";
    request.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    });
    request.addEventListener("load", () => {
      if (request.status >= 200 && request.status < 300) {
        resolve(request.response);
      } else {
        reject(new Error(request.response?.error || `Upload failed (${request.status})`));
      }
    });
    request.addEventListener("error", () => reject(new Error("Network error while posting.")));
    request.send(form);
  });
}

export async function setLike(postId, liked) {
  const response = await fetch(`/api/posts/${postId}/like`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ client_id: getClientId(), liked }),
  });
  return readJson(response);
}
