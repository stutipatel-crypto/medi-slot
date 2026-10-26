/**
 * main.js — Medi Slot client-side helpers.
 *
 * Responsibilities:
 *  1. Mobile nav toggle.
 *  2. Password visibility toggle.
 *  3. Flash message dismiss.
 *  4. Tab switching on My Appointments page.
 *  5. Dynamic slot loading when the booking date changes.
 *  6. Doctor image fallback.
 */

(function () {
  "use strict";

  // -------------------------------------------------------------------------
  // 1. Mobile navigation toggle
  // -------------------------------------------------------------------------
  const hamburger = document.querySelector(".hamburger");
  const navMenu   = document.querySelector(".navbar-nav");

  if (hamburger && navMenu) {
    hamburger.addEventListener("click", () => {
      const open = navMenu.classList.toggle("open");
      hamburger.setAttribute("aria-expanded", open);
    });

    // Close nav when a link is clicked
    navMenu.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => navMenu.classList.remove("open"));
    });
  }

  // -------------------------------------------------------------------------
  // 2. Password visibility toggle
  // -------------------------------------------------------------------------
  document.querySelectorAll(".toggle-pwd").forEach((btn) => {
    btn.addEventListener("click", () => {
      const input = btn.closest(".password-wrap").querySelector("input");
      if (!input) return;
      const isText = input.type === "text";
      input.type = isText ? "password" : "text";
      btn.innerHTML = isText
        ? '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>'
        : '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>';
      btn.setAttribute("aria-label", isText ? "Show password" : "Hide password");
    });
  });

  // -------------------------------------------------------------------------
  // 3. Flash message dismiss
  // -------------------------------------------------------------------------
  document.querySelectorAll(".alert-dismiss").forEach((btn) => {
    btn.addEventListener("click", () => {
      btn.closest(".alert").remove();
    });
  });

  // -------------------------------------------------------------------------
  // 4. Tab switching (My Appointments)
  // -------------------------------------------------------------------------
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = btn.dataset.tab;
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));
      btn.classList.add("active");
      const panel = document.getElementById("tab-" + target);
      if (panel) panel.classList.add("active");
    });
  });

  // -------------------------------------------------------------------------
  // 5. Dynamic time-slot loading on booking / reschedule pages
  // -------------------------------------------------------------------------
  const dateInput  = document.getElementById("appointment_date");
  const slotSelect = document.getElementById("appointment_time");
  const excludeId  = document.getElementById("exclude_appointment_id");

  if (dateInput && slotSelect) {
    dateInput.addEventListener("change", fetchSlots);

    function fetchSlots() {
      const dateVal = dateInput.value;
      if (!dateVal) return;
      const excludeParam = excludeId ? `&exclude=${excludeId.value}` : "";
      slotSelect.innerHTML = '<option value="">Loading slots…</option>';
      slotSelect.disabled = true;

      fetch(`/api/slots?date=${dateVal}${excludeParam}`)
        .then((r) => r.json())
        .then((data) => {
          slotSelect.innerHTML = "";
          slotSelect.disabled = false;
          if (data.error) {
            slotSelect.innerHTML = '<option value="">Error loading slots</option>';
            return;
          }
          if (!data.slots || data.slots.length === 0) {
            slotSelect.innerHTML = '<option value="">No slots available</option>';
            return;
          }
          data.slots.forEach((slot) => {
            const opt = document.createElement("option");
            opt.value = slot;
            opt.textContent = formatSlot(slot);
            slotSelect.appendChild(opt);
          });
        })
        .catch(() => {
          slotSelect.innerHTML = '<option value="">Could not load slots</option>';
          slotSelect.disabled = false;
        });
    }

    function formatSlot(slot) {
      // Convert "09:00" → "09:00 AM" etc.
      try {
        const [h, m] = slot.split(":").map(Number);
        const period = h < 12 ? "AM" : "PM";
        const displayH = h % 12 || 12;
        return `${String(displayH).padStart(2, "0")}:${String(m).padStart(2, "0")} ${period}`;
      } catch {
        return slot;
      }
    }
  }

  // -------------------------------------------------------------------------
  // 6. Doctor profile image fallback
  // -------------------------------------------------------------------------
  document.querySelectorAll("img.doctor-avatar, img.profile-avatar").forEach((img) => {
    img.addEventListener("error", () => {
      img.src = "/static/images/doctor-placeholder.svg";
      img.alt = "Doctor profile image unavailable";
    });
  });

})();
