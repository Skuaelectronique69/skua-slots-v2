const API_URL = "http://100.121.68.48:8011";

export async function serverSpin(state) {
  const response = await fetch(`${API_URL}/api/spin`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      player_id: "DEV_OP",
      energy: state.energy,
      xp: state.xp,
      credits: state.credits,
    }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Spin API ${response.status}: ${text}`);
  }

  return await response.json();
}
