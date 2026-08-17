/**
 * Parent and student reviews, supplied by the owner on 2026-08-18.
 *
 * These are real people. Two things follow from that:
 *
 *  1. The wording is theirs. Light punctuation and spelling tidying only —
 *     nothing has been embellished, strengthened, or invented.
 *  2. Names are published as given. If anyone asks to be removed, delete the
 *     entry here and it disappears from the site immediately.
 *
 * `context` is the reviewer's relationship to SS Tuitions, used as a small
 * label on the card. It carries more weight than a star rating because it is
 * specific and checkable.
 */

export interface Testimonial {
  name: string;
  context: string;
  quote: string;
}

export const testimonials: Testimonial[] = [
  {
    name: "Manaswini Sudagoni",
    context: "Grade 6 CBSE",
    quote:
      "My child joined SS Tuitions for Grade 6 CBSE home tuition last year. The progress has been steady throughout the year. The tutor focuses on understanding concepts rather than memorising answers. We plan to continue with SS Tuitions.",
  },
  {
    name: "Anvesh Mamidi",
    context: "JEE small batch",
    quote:
      "We joined our child in the online JEE small batch of only 4 students. The interaction is very good, and every student gets enough time to ask doubts. We are satisfied with the personal attention provided.",
  },
  {
    name: "Phani Keerthan Reddy Mucha",
    context: "JEE Advanced · one-to-one",
    quote:
      "My daughter is taking one-on-one Physics coaching for JEE Advanced, and her conceptual understanding has improved a lot. The mentor focuses on problem-solving techniques and exam strategy. Highly recommended for serious JEE aspirants.",
  },
  {
    name: "Madhura Neeli",
    context: "JEE Main & Advanced",
    quote:
      "SS Tuitions offers excellent online coaching for JEE Main and Advanced. My daughter attends Maths, Physics and Chemistry classes regularly. The teachers explain concepts patiently, and the fees are affordable compared with other coaching institutes.",
  },
  {
    name: "Siddhartha Chintalapudi",
    context: "Online Chemistry",
    quote:
      "We enrolled our daughter in online Chemistry classes, and the improvement in her test scores is clearly visible. The teacher provides notes, assignments and regular revision sessions.",
  },
  {
    name: "Manasa Dornala",
    context: "Class 7 ICSE",
    quote:
      "We enrolled our Class 7 ICSE child in SS Tuitions last year, and it has been a very positive experience. The teacher is punctual, dedicated and genuinely cares about student progress.",
  },
  {
    name: "Saroj Kumawat",
    context: "Parent",
    quote:
      "Excellent tutor with great teaching skills. Concepts were explained clearly and patiently, making learning easy and enjoyable. Highly recommended!",
  },
  {
    name: "Aravind Gugulothu",
    context: "Parent",
    quote:
      "I'm satisfied with the quality of teaching. My child's interest in studies has improved significantly.",
  },
  {
    name: "Pinky Poo",
    context: "Parent",
    quote:
      "SS Tuitions connects us with good tutors very quickly. The service is immediate and the coordination is professional. Highly recommended for parents.",
  },
  {
    name: "Bhukya Vinod",
    context: "Parent",
    quote:
      "As a parent, I'm thankful to SS Tuitions. They have helped improve my child's academic performance.",
  },
  {
    name: "Bhanu Elagandula",
    context: "Parent",
    quote:
      "The way of teaching is very good. The tutors explain topics in different ways so that children can understand them easily.",
  },
  {
    name: "Karthikeya Gupta",
    context: "Chemistry",
    quote:
      "The teachers and their way of teaching are very good. My son got good marks after studying with their Chemistry teacher.",
  },
  {
    name: "Saidivya Vankudoth",
    context: "Manikonda",
    quote:
      "I'm very glad to send my children to such a good academy. The tutors provide value beyond academics and make it easier for students to complete their homework. Highly recommended in the Manikonda area.",
  },
  {
    name: "Nikhileswar Ambati",
    context: "Parent",
    quote:
      "I joined my son here. The tutors are excellent, and I've noticed a clear improvement in his grades.",
  },
  {
    name: "Dinesh Varma",
    context: "Parent",
    quote:
      "We joined our daughter here and she is getting better. They also accommodate our timings very well. Good job!",
  },
  {
    name: "Vaishnavi Balla",
    context: "Home tuition",
    quote:
      "These tuitions are very helpful for students. Experienced tutors come to your doorstep and teach the children.",
  },
  {
    name: "Nikhil Royal Srikara",
    context: "Parent",
    quote:
      "We had a really great experience. SS Tuitions provides excellent service with experienced and qualified tutors.",
  },
  {
    name: "Naga Surendar Reddy Sheelam",
    context: "Home tuition",
    quote:
      "SS Tuitions is the best in all aspects. I strongly recommend them for all types of home tuition.",
  },
  {
    name: "Venkanna Nethavath",
    context: "Parent",
    quote:
      "My son is scoring better marks after joining SS Tuitions. We are very happy with the support.",
  },
  {
    name: "Rajesh Banoth",
    context: "Parent",
    quote:
      "My son has improved a lot after joining SS Tuitions. The teachers are patient, supportive, and explain every topic clearly.",
  },
];

/** Initials for the avatar chip, e.g. "Anvesh Mamidi" -> "AM". */
export function initialsOf(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase())
    .join("");
}
