interface FooterProps {
  renderCount: number | null;
}

function Footer({ renderCount }: FooterProps) {
  const count = renderCount?.toLocaleString() ?? "0";

  return (
    <footer className="site-footer">
      Version 1.1.0 published 07/25/2026 by Tyler "Tyro" Crews. Successfully generated {count} podium
      images for the Melee community <span aria-label="love">{"\u{1F495}"}</span>
    </footer>
  );
}

export default Footer;
