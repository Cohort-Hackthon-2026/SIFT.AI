let getTokenFn = null;

export function setTokenGetter(fn) {
  getTokenFn = fn;
}

export function getOrCreateGuestId() {
  try {
    let guestId = localStorage.getItem("sift_guest_session_id");
    if (!guestId) {
      guestId = `guest_${crypto.randomUUID()}`;
      localStorage.setItem("sift_guest_session_id", guestId);
    }
    return guestId;
  } catch {
    return "guest_browser_session";
  }
}

export async function getAuthToken() {
  try {
    if (getTokenFn) {
      const token = await getTokenFn();
      if (token) return token;
    }
  } catch {
    // Guest or unauthenticated fallback
  }
  return getOrCreateGuestId();
}

