import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "Reel Good — find your next favorite film",
  description: "Rate a few films and discover your next movie night pick with a transparent recommendation model.",
  openGraph: {
    title: "Reel Good — find your next favorite film",
    description: "A movie discovery demo powered by Spark ALS.",
    type: "website",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
