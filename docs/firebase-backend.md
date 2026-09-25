# Firebase backend

The Flask server uses the Firebase Admin SDK for three responsibilities:

- verify Firebase Authentication ID tokens;
- store user-owned entrant and layout documents in Cloud Firestore;
- store user-uploaded raster images in Cloud Storage for Firebase.

The service-account JSON is a runtime secret and is never copied into the
repository, frontend bundle, or deployment ZIP.

## Runtime configuration

Set these values in the local ignored `.env` and in the hosting provider's
private Python application environment (or an external dotenv file stored
outside the application and public web root):

```dotenv
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/firebase-admin.json
FIREBASE_STORAGE_BUCKET=the-exact-bucket-name-from-firebase-console
```

Hosted deployments may optionally set `PODIUM_SECRETS_FILE` to an absolute path
for an external dotenv file. When it is omitted, the application checks for a
file named `melee-podium-secrets` in the hosting account's home directory. In
either case, keep that file outside the application and public web root.

Do not prefix the bucket with a URL. A leading `gs://` is accepted and removed,
but the plain bucket name is preferred. Restart the cPanel Python application
after changing its environment.

Optional settings:

```dotenv
FIREBASE_CHECK_REVOKED_TOKENS=false
FIREBASE_MAX_IMAGE_BYTES=314572800
```

Revocation checks are disabled by default because enabling them adds an
Authentication lookup to each protected request. Ordinary ID-token signature
and expiry verification always occurs.

## Browser authentication flow

The React UI uses the Firebase Web SDK with Google sign-in. Copy
`frontend/.env.example` to `frontend/.env.local` and fill in the public Web app
configuration from Firebase Console. Enable Google as a provider under
Authentication > Sign-in method, and add each deployed hostname to the
authorized domains list.

The UI obtains the signed-in user's Firebase ID token and sends it to Flask over
HTTPS:

```http
Authorization: Bearer <Firebase ID token>
```

Flask verifies the token and uses only its verified `uid` when selecting a
Firestore collection or Storage path. The API never trusts a user ID supplied
by the browser.

## Firestore structure

Firestore stores JSON-like documents, rather than JSON files in folders:

```text
users/{uid}/layouts/{layoutId}
users/{uid}/entrants/{entrantId}
users/{uid}/images/{imageId}
```

Layout and entrant request bodies use this envelope:

```json
{
  "name": "Weekly stream layout",
  "data": {
    "schema-specific": "values belong here"
  }
}
```

The server adds document IDs, schema versions, and timestamps. Layouts should
refer to an uploaded image by its stable `imageId`, not by its temporary signed
download URL. Each saved document is limited to 900,000 bytes so Firestore's
document overhead remains below its platform limit.

## API groundwork

All endpoints except `/api/firebase/status` require the bearer token above.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/firebase/status` | Non-secret server configuration status |
| `GET` | `/api/firebase/me` | Verified current-user summary |
| `GET`, `POST` | `/api/firebase/layouts` | List or create layouts |
| `GET`, `PUT`, `DELETE` | `/api/firebase/layouts/{id}` | Read, replace, or delete a layout |
| `GET`, `POST` | `/api/firebase/entrants` | List or create entrants |
| `GET`, `PUT`, `DELETE` | `/api/firebase/entrants/{id}` | Read, replace, or delete an entrant |
| `GET`, `POST` | `/api/firebase/images` | List metadata or upload multipart `file`, `name`, and `category` fields |
| `GET`, `DELETE` | `/api/firebase/images/{id}` | Read metadata or delete an image |
| `POST` | `/api/firebase/images/{id}/download-url` | Create a private 15-minute download URL |

Image uploads accept validated PNG, JPG/JPEG, WebP, GIF, and BMP raster content up to 300 MiB by
default. The server ignores a claimed MIME type, inspects the actual bytes, uses a generated Storage path, and
stores dimensions and other metadata in Firestore. `category` must be either
`tournament_logo` or `background`. Names are unique case-insensitively within a
category, and each account can store up to 10 images in each category.

## Firebase security rules

The current design sends Firestore and Storage operations through Flask. Admin
SDK calls use IAM and bypass Firebase Security Rules, while Flask enforces user
ownership from the verified token. Until direct browser access is deliberately
implemented, client rules can deny all Firestore and Storage access:

```text
allow read, write: if false;
```

Do not leave either service in Firebase's temporary test mode. If image uploads
later move directly to the browser, add narrowly scoped rules for
`users/{uid}/...` and test those rules before enabling client writes.
