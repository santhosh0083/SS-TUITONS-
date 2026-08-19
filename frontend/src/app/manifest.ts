import type { MetadataRoute } from "next";

/**
 * The web app manifest, which is what makes the site installable.
 *
 * Once installed, this is indistinguishable from a store app for the people
 * using it: an icon on the home screen that opens fullscreen with no browser
 * chrome. It is not in any store, so there is no review, no yearly fee, and
 * an update reaches everyone the moment it deploys rather than after a
 * download.
 *
 * start_url is /login rather than "/" deliberately. The marketing homepage is
 * for people deciding whether to sign up; someone who has installed the app
 * has already decided, and wants to get in.
 */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "SS Tuitions",
    short_name: "SS Tuitions",
    description:
      "Classes, attendance, fees and messages for SS Tuitions students, " +
      "parents and tutors.",
    start_url: "/login",
    scope: "/",
    display: "standalone",
    orientation: "portrait",
    background_color: "#14213d",
    theme_color: "#14213d",
    lang: "en-IN",
    categories: ["education"],
    icons: [
      {
        src: "/icons/icon-192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icons/icon-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "any",
      },
      {
        // Android crops this one to whatever shape the launcher uses, so it
        // carries extra padding around the artwork.
        src: "/icons/maskable-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
    ],
    // Only routes every role can reach. The dashboards are role-specific
    // (/admin, /parent, /student, /tutor), so a shortcut to any one of them
    // would be a dead end for everybody else -- and a long-press menu that
    // leads somewhere broken is worse than a short one.
    shortcuts: [
      {
        name: "Messages",
        url: "/messages",
        description: "Conversations with tutors and parents",
      },
    ],
  };
}
