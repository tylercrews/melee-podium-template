import { FirebaseApp, getApp, getApps, initializeApp } from "firebase/app";
import {
  Auth,
  GoogleAuthProvider,
  User,
  getAuth,
  onAuthStateChanged,
  signInWithPopup,
  signOut,
} from "firebase/auth";

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY?.trim(),
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN?.trim(),
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID?.trim(),
  appId: import.meta.env.VITE_FIREBASE_APP_ID?.trim(),
};

export const firebaseAuthAvailable = Object.values(firebaseConfig).every(Boolean);

let app: FirebaseApp | null = null;
let auth: Auth | null = null;

function configuredAuth(): Auth {
  if (!firebaseAuthAvailable) {
    throw new Error("Sign-in is not configured for this deployment yet.");
  }
  if (!app) app = getApps().length ? getApp() : initializeApp(firebaseConfig);
  if (!auth) auth = getAuth(app);
  return auth;
}

export function watchCurrentUser(listener: (user: User | null) => void): () => void {
  if (!firebaseAuthAvailable) {
    listener(null);
    return () => undefined;
  }
  return onAuthStateChanged(configuredAuth(), listener);
}

export async function signInWithGoogle(): Promise<User> {
  const result = await signInWithPopup(configuredAuth(), new GoogleAuthProvider());
  return result.user;
}

export async function signOutCurrentUser(): Promise<void> {
  if (firebaseAuthAvailable) await signOut(configuredAuth());
}

export type { User };
