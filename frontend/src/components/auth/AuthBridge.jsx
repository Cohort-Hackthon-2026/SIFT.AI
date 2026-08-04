import { useEffect } from "react";
import { useAuth } from "@clerk/react";
import { setTokenGetter } from "../../lib/authBridge";

export default function AuthBridge() {
  const { getToken } = useAuth();

  useEffect(() => {
    setTokenGetter(getToken);
  }, [getToken]);

  return null;
}
