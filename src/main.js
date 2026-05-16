import { initTelegramWebApp } from "./telegram.js";
import { serverSpin, fetchLeaderboard, fetchMe, fetchWallet, fetchWalletHistory, fetchStreak, claimStreak } from "./api.js";

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


function labelReason(reason) {
  if (reason === "streak_reward") return "Daily streak";
  if (reason === "spin_reward") return "Spin";
  if (reason === "admin_mint") return "Dev mint";
  if (reason === "mission_reward") return "Mission";
  return reason;
}

async function refreshEconomy() {
  try {
    const [wallet, streak, history] = await Promise.all([
      fetchWallet(),
      fetchStreak(),
      fetchWalletHistory(10, 0),
    ]);

    document.getElementById("sku-balance").textContent = wallet.balance_sku ?? wallet.credits ?? wallet.new_balance ?? 0;
    document.getElementById("streak-current").textContent = streak.current_streak ?? streak.streak_days ?? 0;
    document.getElementById("streak-best").textContent = streak.best_streak ?? 0;

    const claimBtn = document.getElementById("claim-daily");
    claimBtn.disabled = streak.claimed_today;
    claimBtn.textContent = streak.claimed_today ? "CLAIMED TODAY" : "CLAIM DAILY";

    const rows = history.rows || [];
    document.getElementById("wallet-history").innerHTML = rows.length
      ? `<ul>${rows.map((tx) => `
          <li><b>${tx.delta >= 0 ? "+" : ""}${tx.delta} SKU</b> — ${labelReason(tx.reason)}</li>
        `).join("")}</ul>`
      : "<p>Aucune transaction.</p>";
  } catch (err) {
    console.error(err);
    document.getElementById("wallet-history").innerHTML = "<p>Économie indisponible.</p>";
  }
}

document.getElementById("claim-daily")?.addEventListener("click", async () => {
  const btn = document.getElementById("claim-daily");
  btn.disabled = true;
  btn.textContent = "CLAIM...";
  try {
    const result = await claimStreak();
    if (result.claimed) {
      render(`Daily claim validé : +${result.reward ?? 0} SKU · streak ${result.streak_days ?? 0} jour(s).`);
    } else {
      render("Daily claim déjà récupéré aujourd'hui.");
    }
  } catch (err) {
    console.error(err);
    render(`Erreur claim : ${err.message}`);
  }
  await refreshEconomy();
});


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
        ${items.map((r) => `
          <li><b>#${r.rank}</b> ${r.username || r.player_id || "player"} — ${r.score ?? r.xp ?? 0} pts · ${r.best_win ?? r.credits ?? 0} best</li>
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
  await refreshEconomy();
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
  initTelegramWebApp();
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
  await refreshEconomy();
}

boot();

