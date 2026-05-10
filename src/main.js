import { serverSpin, fetchLeaderboard, fetchMe } from "./api.js";

const state = {
  energy: 100,
  xp: 0,
  credits: 500,
  grade: "RECRUIT",
  spins: 0,
  isSpinning: false,
};

const slots = document.querySelectorAll("#slots div");
const btn = document.getElementById("spin");

function render(message = "Mission active : lancer 5 spins.") {
  document.getElementById("energy").textContent = state.energy;
  document.getElementById("xp").textContent = state.xp;
  document.getElementById("credits").textContent = state.credits;
  document.getElementById("grade").textContent = state.grade;
  document.getElementById("message").textContent = message;
}

async function refreshLeaderboard() {
  const root = document.getElementById("leaderboard");

  try {
    const data = await fetchLeaderboard();

    if (!data.items || data.items.length === 0) {
      root.innerHTML = "<p>Aucun joueur classé.</p>";
      return;
    }

    root.innerHTML = `
      <ol>
        ${data.items.map((r) => `
          <li><b>#${r.rank}</b> ${r.player_id} — ${r.xp} XP · ${r.credits} crédits</li>
        `).join("")}
      </ol>
    `;
  } catch (err) {
    root.innerHTML = `<p>Classement indisponible.</p>`;
    console.error(err);
  }
}

btn.onclick = async () => {
  if (state.isSpinning) return;

  state.isSpinning = true;
  btn.disabled = true;
  btn.textContent = "SPIN EN COURS...";

  try {
    const result = await serverSpin();

    if (!result.accepted) {
      render("Énergie insuffisante. Recharge réseau nécessaire.");
      return;
    }

    result.reels.forEach((symbol, index) => {
      slots[index].textContent = symbol;
    });

    state.energy = result.energy_after;
    state.xp = result.xp_after;
    state.credits = result.credits_after;
    state.grade = result.grade;
    state.spins += 1;

    if (result.result === "jackpot") {
      render(`JACKPOT serveur : +${result.payout} crédits, +${result.xp_gained} XP.`);
    } else if (result.result === "win") {
      render(`Gain serveur : +${result.payout} crédits, +${result.xp_gained} XP.`);
    } else {
      render(`Spin serveur ${state.spins}/5 enregistré. +${result.xp_gained} XP.`);
    }

    await refreshLeaderboard();
  } catch (err) {
    console.error(err);
    render(`Erreur API : ${err.message}`);
  } finally {
    state.isSpinning = false;
    btn.disabled = false;
    btn.textContent = "SPIN · 10 ENERGY";
  }
};


async function boot() {
  try {
    const me = await fetchMe();
    if (me.authenticated) {
      state.energy = me.energy;
      state.xp = me.xp;
      state.credits = me.credits;
      state.grade = "RECRUIT";
      render(`Connecté : ${me.player_id}`);
    } else {
      render("Authentification impossible.");
    }
  } catch (err) {
    console.error(err);
    render(`Erreur auth : ${err.message}`);
  }

  await refreshLeaderboard();
}

boot();

