import { useEffect, useRef } from "react";

interface ContactDialogProps {
  onClose: () => void;
}

export default function ContactDialog({ onClose }: ContactDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    dialogRef.current?.showModal();
  }, []);

  return <dialog id="tyro-contact-dialog" ref={dialogRef} className="shoutouts-dialog contact-dialog" aria-labelledby="tyro-contact-title" onClose={onClose} onClick={(event) => {
    if (event.target === event.currentTarget) onClose();
  }}>
    <div className="shoutouts-dialog__content">
      <div className="shoutouts-dialog__heading">
        <h2 id="tyro-contact-title">Bugs and feature requests</h2>
        <button type="button" aria-label="Close contact information" onClick={onClose}>
          <svg aria-hidden="true" viewBox="0 0 24 24" focusable="false"><path d="M6 6 18 18M18 6 6 18" /></svg>
        </button>
      </div>
      <p>If you have any bugs or feature requests, you can try to reach out to me:</p>
      <ul>
        <li>Bluesky: <a href="https://bsky.app/profile/tyrowo.com" target="_blank" rel="noreferrer">@tyrowo.com</a></li>
        <li>Discord: @tyrowo</li>
        <li>Email: <a href="mailto:tylerpcrews@gmail.com">tylerpcrews@gmail.com</a></li>
      </ul>
    </div>
  </dialog>;
}
