import type { Metadata } from "next";
import { Inter } from "next/font/google";
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
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} h-full antialiased`}>
      <body className="min-h-full">{children}</body>
    </html>
  );
}
