/**
 * Business details for SS Tuitions.
 *
 * Single source of truth for anything shown publicly. Components import from
 * here rather than hardcoding, so a changed phone number is one edit.
 *
 * Values supplied by the owner on 2026-08-18. Anything not yet supplied stays
 * as null and is simply not rendered — never invented, never a placeholder
 * shown to a parent.
 */

export const site = {
  name: "SS Tuitions",

  phone: {
    /** E.164, for tel: and wa.me links. */
    e164: "+917799891976",
    /** Human-readable. */
    display: "+91 77998 91976",
  },

  /** Assumed to be the same line as `phone`. Confirm before relying on it. */
  whatsapp: "917799891976",

  email: "sstuitions42@gmail.com",

  address: {
    area: "Kokapet",
    city: "Hyderabad",
    state: "Telangana",
    pincode: "500075",
    get short() {
      return `${this.area}, ${this.city}`;
    },
    get full() {
      return `${this.area}, ${this.city}, ${this.state} ${this.pincode}`;
    },
  },

  /** Not yet supplied — see docs/INTAKE.md Group B. */
  hours: null as string | null,

  social: {
    instagram: {
      handle: "ss_tuitions_",
      url: "https://instagram.com/ss_tuitions_",
    },
    facebook: null,
    youtube: null,
  },
} as const;

/** Pre-filled WhatsApp message so an enquiry arrives with context. */
export function whatsappLink(message?: string): string {
  const text = encodeURIComponent(
    message ??
      "Hi, I would like to know about tuition classes for my child.",
  );
  return `https://wa.me/${site.whatsapp}?text=${text}`;
}
