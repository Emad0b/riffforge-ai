import "./globals.css";
export const metadata = {
  title: "RiffForge AI · Transcription studio",
  description:
    "From a riff to a playable guitar tab. Real Basic Pitch inference with editable fingerings.",
};
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
