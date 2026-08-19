import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";

import { InstallPrompt } from "@/components/app/InstallPrompt";
import { ServiceWorker } from "@/components/app/ServiceWorker";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "SS Tuitions — Home & Online Tuition in Hyderabad, Grade 1 to 12",
    template: "%s · SS Tuitions",
  },
  description:
    "Home and online tuition for Grades 1 to 12 in Kokapet, Hyderabad. All subjects, " +
    "IIT tutors and professional teachers, flexible timings and affordable fees. " +
    "JEE, NEET, EAMCET, IPE and SAT preparation.",
  keywords: [
    "tuition Hyderabad",
    "home tuition Kokapet",
    "online tuition Grade 1 to 12",
    "IIT tutors Hyderabad",
    "JEE NEET EAMCET coaching",
  ],
  openGraph: {
    title: "SS Tuitions — Home & Online Tuition in Hyderabad",
    description:
      "Grades 1 to 12, all subjects. IIT tutors and professional teachers, " +
      "flexible timings, affordable fees.",
    locale: "en_IN",
    type: "website",
  },
  // iOS does not read the web manifest for these, so they are declared here
  // as well or an installed icon falls back to a screenshot of the page.
  appleWebApp: {
    capable: true,
    title: "SS Tuitions",
    statusBarStyle: "black-translucent",
  },
  icons: {
    icon: "/icons/icon-192.png",
    apple: "/icons/apple-touch-icon.png",
  },
};

export const viewport: Viewport = {
  // Paints the phone's status bar navy so an installed app looks continuous
  // with its own header rather than sitting under a white strip.
  themeColor: "#14213d",
  // Fills the notch area on iPhones, which the translucent status bar above
  // requires to avoid content hiding behind the notch.
  viewportFit: "cover",
  width: "device-width",
  initialScale: 1,
  // Not locked down: pinch-zoom is an accessibility feature, and a parent
  // reading a fee amount on a small phone may need it.
  maximumScale: 5,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} h-full antialiased`}>
      <body className="min-h-full">
        {children}
        <InstallPrompt />
        <ServiceWorker />
      </body>
    </html>
  );
}
