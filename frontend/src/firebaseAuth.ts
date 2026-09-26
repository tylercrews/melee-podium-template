import { FirebaseApp, FirebaseError, getApp, getApps, initializeApp } from "firebase/app";
import {
  Auth,
  GoogleAuthProvider,
  User,
  createUserWithEmailAndPassword,
  getAuth,
  onAuthStateChanged,
  signInWithEmailAndPassword,
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

export async function signInWithEmail(email: string, password: string): Promise<User> {
  const result = await signInWithEmailAndPassword(configuredAuth(), email, password);
  return result.user;
}

export async function createAccountWithEmail(email: string, password: string): Promise<User> {
  const result = await createUserWithEmailAndPassword(configuredAuth(), email, password);
  return result.user;
}

export function firebaseAuthErrorMessage(error: unknown): string {
  if (!(error instanceof FirebaseError)) {
    return error instanceof Error ? error.message : "Authentication failed. Please try again.";
  }
  const messages: Record<string, string> = {
    "auth/email-already-in-use": "An account already exists for that email address.",
    "auth/invalid-credential": "The email or password is incorrect.",
    "auth/invalid-email": "Enter a valid email address.",
    "auth/missing-password": "Enter your password.",
    "auth/network-request-failed": "The sign-in service could not be reached. Check your connection and try again.",
    "auth/too-many-requests": "Too many attempts were made. Wait a moment and try again.",
    "auth/user-disabled": "This account has been disabled.",
    "auth/weak-password": "Use a stronger password with at least six characters.",
  };
  return messages[error.code] ?? "Authentication failed. Please try again.";
}

export async function signOutCurrentUser(): Promise<void> {
  if (firebaseAuthAvailable) await signOut(configuredAuth());
}

export type { User };
