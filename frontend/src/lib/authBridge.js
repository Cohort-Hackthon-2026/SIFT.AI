let getTokenFn = null;

export function setTokenGetter(fn) {
  getTokenFn = fn;
}

export async function getAuthToken() {
  if (!getTokenFn) {
    throw new Error("Auth isn't ready yet");
  }
  return getTokenFn();
}
