import { useEffect, useRef, useState } from "react";

interface FooterProps {
  renderCount: number | null;
}

function Footer({ renderCount }: FooterProps) {
  const count = renderCount?.toLocaleString() ?? "0";
  const [isShoutoutsOpen, setIsShoutoutsOpen] = useState(false);
  const shoutoutsDialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    if (isShoutoutsOpen) shoutoutsDialogRef.current?.showModal();
  }, [isShoutoutsOpen]);

  return (
    <>
      <footer className="site-footer">
        <div>
          Version 1.3 published 07/29/2026 by Tyler "Tyro" Crews. Successfully generated {count} podium
          images for the Melee community <span aria-label="love">{"\u{1F495}"}</span>
        </div>
        <div>
          Melee Podium Template is free and{" "}
          <a href="https://github.com/tylercrews/melee-podium-template" target="_blank" rel="noreferrer">
            open source
          </a>
          .
        </div>
        <button className="site-footer__shoutouts-button" type="button" onClick={() => setIsShoutoutsOpen(true)}>
          Thank yous and shoutouts.
        </button>
      </footer>

      {isShoutoutsOpen && (
        <dialog ref={shoutoutsDialogRef} className="shoutouts-dialog" aria-labelledby="shoutouts-title" onClose={() => setIsShoutoutsOpen(false)} onClick={(event) => {
          if (event.target === event.currentTarget) setIsShoutoutsOpen(false);
        }}>
          <div className="shoutouts-dialog__content">
            <div className="shoutouts-dialog__heading">
              <h2 id="shoutouts-title">Thank yous and shoutouts</h2>
              <button type="button" aria-label="Close thank yous and shoutouts" onClick={() => setIsShoutoutsOpen(false)}>
                <svg aria-hidden="true" viewBox="0 0 24 24" focusable="false">
                  <path d="M6 6 18 18M18 6 6 18" />
                </svg>
              </button>
            </div>
            <ul>
              <li><a href="https://x.com/Malarki_" target="_blank" rel="noreferrer">Malarki_</a>, who I commissioned to expand the pool of character poses and did an amazing job.</li>
              <li><a href="https://www.top8er.com/" target="_blank" rel="noreferrer">Top8er</a>, an amazing site that my local scene was using all the time, only inspired me to create this podium template because there wasn't an option for doubles. Huge thanks for being <a href="https://github.com/ShonTitor/Top8er" target="_blank" rel="noreferrer">open source</a> (shouts out to ShonTitor, agiera, and jmlee337); it was a huge help for figuring out the start.gg and Challonge bracket importing.</li>
              <li>AeonSSB, Cjag01, radzo73, and caha1an, who created the <a href="https://github.com/AeonSSB/Melee-CSProject" target="_blank" rel="noreferrer">Melee-CSProject</a> that I got the original poses from.</li>
              <li><a href="https://smashboards.com/threads/character-stock-icon-dump.390494/" target="_blank" rel="noreferrer">CeLL on this old Smashboards thread</a> for posting a dump of all the character stock icons.</li>
              <li><a href="https://www.spriters-resource.com/gamecube/ssbm/asset/46039/" target="_blank" rel="noreferrer">Mr. C</a> for the Sheik stock icons.</li>
              <li>Also shoutout to <a href="https://smashboards.com/" target="_blank" rel="noreferrer">SmashBoards</a> in general - what�what an amazing site still.</li>
              <li>North Carolina Melee!! Love y'all.</li>
            </ul>
          </div>
        </dialog>
      )}
    </>
  );
}

export default Footer;
