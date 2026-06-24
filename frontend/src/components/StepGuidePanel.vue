<template>
  <section class="step-guide" :class="`variant-${variant}`">
    <div class="guide-art">
      <svg v-if="variant === 'planner'" viewBox="0 0 420 220" aria-hidden="true">
        <defs>
          <linearGradient id="plannerSky" x1="0" x2="1" y1="0" y2="1">
            <stop offset="0%" stop-color="#0f766e" />
            <stop offset="100%" stop-color="#1d4ed8" />
          </linearGradient>
        </defs>
        <rect x="10" y="14" width="400" height="192" rx="28" fill="url(#plannerSky)" />
        <circle cx="88" cy="74" r="28" fill="rgba(255,255,255,0.15)" />
        <circle cx="88" cy="74" r="14" fill="#f8fafc" />
        <path d="M88 88l18 28 28-36 36 54" fill="none" stroke="#bbf7d0" stroke-width="10" stroke-linecap="round" stroke-linejoin="round" />
        <rect x="174" y="48" width="172" height="26" rx="13" fill="rgba(255,255,255,0.14)" />
        <rect x="174" y="88" width="126" height="18" rx="9" fill="rgba(255,255,255,0.16)" />
        <rect x="174" y="118" width="154" height="18" rx="9" fill="rgba(255,255,255,0.12)" />
        <rect x="56" y="142" width="112" height="38" rx="19" fill="#ecfeff" />
        <text x="112" y="166" text-anchor="middle" fill="#0f172a" font-size="18" font-weight="700">Trip brief</text>
        <rect x="196" y="142" width="98" height="38" rx="19" fill="#dbeafe" />
        <text x="245" y="166" text-anchor="middle" fill="#1e3a8a" font-size="18" font-weight="700">Matches</text>
        <rect x="314" y="142" width="60" height="38" rx="19" fill="#dcfce7" />
        <text x="344" y="166" text-anchor="middle" fill="#166534" font-size="18" font-weight="700">Cart</text>
      </svg>

      <svg v-else-if="variant === 'itinerary'" viewBox="0 0 420 220" aria-hidden="true">
        <defs>
          <linearGradient id="itineraryGlow" x1="0" x2="1" y1="0" y2="1">
            <stop offset="0%" stop-color="#f97316" />
            <stop offset="100%" stop-color="#fb7185" />
          </linearGradient>
        </defs>
        <rect x="10" y="14" width="400" height="192" rx="28" fill="#fff7ed" />
        <rect x="30" y="34" width="360" height="152" rx="24" fill="url(#itineraryGlow)" opacity="0.12" />
        <rect x="52" y="46" width="110" height="128" rx="20" fill="#ffffff" stroke="#fed7aa" stroke-width="4" />
        <text x="78" y="76" fill="#9a3412" font-size="18" font-weight="700">Day 1</text>
        <rect x="70" y="92" width="74" height="12" rx="6" fill="#fdba74" />
        <rect x="70" y="114" width="52" height="12" rx="6" fill="#fed7aa" />
        <rect x="70" y="136" width="64" height="12" rx="6" fill="#fed7aa" />
        <path d="M176 110h66" stroke="#f97316" stroke-width="10" stroke-linecap="round" />
        <path d="M232 110l-18-18M232 110l-18 18" stroke="#f97316" stroke-width="10" stroke-linecap="round" stroke-linejoin="round" />
        <rect x="258" y="56" width="118" height="118" rx="28" fill="#ffffff" stroke="#fecdd3" stroke-width="4" />
        <circle cx="317" cy="92" r="24" fill="#ffe4e6" />
        <path d="M306 92h22M317 81v22" stroke="#e11d48" stroke-width="8" stroke-linecap="round" />
        <rect x="286" y="126" width="62" height="16" rx="8" fill="#fda4af" />
        <text x="317" y="162" text-anchor="middle" fill="#9f1239" font-size="16" font-weight="700">Save & share</text>
      </svg>

      <svg v-else viewBox="0 0 420 220" aria-hidden="true">
        <defs>
          <linearGradient id="quoteFlow" x1="0" x2="1" y1="0" y2="1">
            <stop offset="0%" stop-color="#0891b2" />
            <stop offset="100%" stop-color="#0f766e" />
          </linearGradient>
        </defs>
        <rect x="10" y="14" width="400" height="192" rx="28" fill="#ecfeff" />
        <rect x="34" y="38" width="112" height="70" rx="22" fill="#ffffff" stroke="#a5f3fc" stroke-width="4" />
        <circle cx="66" cy="73" r="13" fill="#cffafe" />
        <path d="M66 66v14M59 73h14" stroke="#0891b2" stroke-width="5" stroke-linecap="round" />
        <path d="M90 64h34" stroke="#164e63" stroke-width="8" stroke-linecap="round" opacity="0.3" />
        <path d="M90 82h24" stroke="#06b6d4" stroke-width="8" stroke-linecap="round" opacity="0.8" />

        <path d="M162 73h44" stroke="#06b6d4" stroke-width="10" stroke-linecap="round" />
        <path d="M198 73l-14-14M198 73l-14 14" stroke="#06b6d4" stroke-width="10" stroke-linecap="round" stroke-linejoin="round" />

        <rect x="222" y="38" width="82" height="70" rx="22" fill="#ffffff" stroke="#99f6e4" stroke-width="4" />
        <rect x="242" y="57" width="42" height="30" rx="10" fill="#d1fae5" />
        <path d="M251 72h24" stroke="#0f766e" stroke-width="6" stroke-linecap="round" />
        <path d="M283 73h42" stroke="#14b8a6" stroke-width="10" stroke-linecap="round" />
        <path d="M317 73l-14-14M317 73l-14 14" stroke="#14b8a6" stroke-width="10" stroke-linecap="round" stroke-linejoin="round" />

        <rect x="90" y="130" width="240" height="46" rx="23" fill="url(#quoteFlow)" />
        <circle cx="122" cy="153" r="10" fill="#ecfeff" opacity="0.9" />
        <path d="M145 144h118" stroke="#ecfeff" stroke-width="8" stroke-linecap="round" opacity="0.95" />
        <path d="M145 161h84" stroke="#ccfbf1" stroke-width="7" stroke-linecap="round" opacity="0.92" />
        <circle cx="286" cy="153" r="8" fill="#bbf7d0" />
      </svg>
    </div>

    <div class="guide-copy">
      <span v-if="eyebrow" class="guide-eyebrow">{{ eyebrow }}</span>
      <h2>{{ title }}</h2>
      <p>{{ description }}</p>

      <div class="guide-steps">
        <article v-for="(step, index) in steps" :key="step.title" class="guide-step">
          <span class="step-number">0{{ index + 1 }}</span>
          <div>
            <h3>{{ step.title }}</h3>
            <p>{{ step.detail }}</p>
          </div>
        </article>
      </div>
    </div>
  </section>
</template>

<script setup>
defineProps({
  variant: {
    type: String,
    default: 'planner'
  },
  eyebrow: {
    type: String,
    default: ''
  },
  title: {
    type: String,
    required: true
  },
  description: {
    type: String,
    default: ''
  },
  steps: {
    type: Array,
    default: () => []
  }
})
</script>

<style scoped>
.step-guide {
  display: grid;
  grid-template-columns: minmax(260px, 0.9fr) minmax(0, 1.1fr);
  gap: 1.2rem;
  padding: 1.1rem;
  border-radius: 28px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  background: linear-gradient(180deg, rgba(255,255,255,0.96), rgba(248,250,252,0.94));
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.08);
}

.guide-art {
  display: flex;
  align-items: stretch;
}

.guide-art svg {
  width: 100%;
  height: auto;
  display: block;
}

.guide-copy {
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.guide-eyebrow {
  display: inline-flex;
  width: fit-content;
  margin-bottom: 0.55rem;
  padding: 0.3rem 0.8rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  background: rgba(15, 23, 42, 0.06);
  color: #334155;
}

.guide-copy h2 {
  margin: 0;
  color: #0f172a;
  font-size: clamp(1.25rem, 2vw, 1.8rem);
  line-height: 1.1;
}

.guide-copy > p {
  margin: 0.65rem 0 1rem;
  color: #475569;
  line-height: 1.6;
}

.guide-steps {
  display: grid;
  gap: 0.7rem;
}

.guide-step {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.8rem;
  padding: 0.85rem 0.9rem;
  border-radius: 18px;
  background: rgba(255,255,255,0.9);
  border: 1px solid rgba(226, 232, 240, 0.9);
}

.step-number {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.4rem;
  height: 2.4rem;
  border-radius: 14px;
  font-size: 0.82rem;
  font-weight: 800;
  color: #fff;
  background: linear-gradient(135deg, #0f766e, #0ea5e9);
}

.guide-step h3 {
  margin: 0 0 0.2rem;
  font-size: 0.98rem;
  color: #0f172a;
}

.guide-step p {
  margin: 0;
  color: #64748b;
  font-size: 0.88rem;
  line-height: 1.5;
}

.variant-itinerary .step-number {
  background: linear-gradient(135deg, #f97316, #ef4444);
}

.variant-quote .step-number {
  background: linear-gradient(135deg, #0891b2, #0f766e);
}

@media (max-width: 900px) {
  .step-guide {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .step-guide {
    padding: 0.9rem;
    border-radius: 22px;
  }

  .guide-step {
    grid-template-columns: 1fr;
  }
}
</style>