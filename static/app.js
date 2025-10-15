// ----------- State -----------
let preparedChunks = [];
let currentIndex = 0;
let speaking = false;
let paused = false;
let currentUtterance = null;
let selectedVoice = null;

// Controls
const fileInput = document.getElementById("pdfFile");
const uploadBtn = document.getElementById("uploadBtn");
const prepStatus = document.getElementById("prepStatus");

const playBtn = document.getElementById("playBtn");
const pauseBtn = document.getElementById("pauseBtn");
const resumeBtn = document.getElementById("resumeBtn");
const stopBtn = document.getElementById("stopBtn");

const voiceSelect = document.getElementById("voiceSelect");
const refreshVoicesBtn = document.getElementById("refreshVoices");

const rate = document.getElementById("rate");
const pitch = document.getElementById("pitch");
const volume = document.getElementById("volume");
const rateVal = document.getElementById("rateVal");
const pitchVal = document.getElementById("pitchVal");
const volumeVal = document.getElementById("volumeVal");

const progressBar = document.getElementById("progressBar");
const progressText = document.getElementById("progressText");
const nowReading = document.getElementById("nowReading");

// Gender quick-pick
const genderRadios = document.querySelectorAll('input[name="gender"]');

// ----------- Helpers -----------
function setStatus(msg, good = true) {
  prepStatus.classList.remove("hidden");
  prepStatus.textContent = msg;
  prepStatus.style.borderColor = good ? "#3656d3" : "#ff5c73";
}

function setProgress(percent) {
  progressBar.style.width = `${percent}%`;
  progressText.textContent = `${Math.round(percent)}%`;
}

function updateControls() {
  playBtn.disabled = preparedChunks.length === 0 || speaking;
  pauseBtn.disabled = !speaking || paused;
  resumeBtn.disabled = !paused;
  stopBtn.disabled = !speaking;
}

function splitPreviewText(txt, max = 250) {
  return txt.length > max ? txt.slice(0, max) + "…" : txt;
}

function inferGenderFromVoiceName(name) {
  const n = (name || "").toLowerCase();
  if (n.includes("zira") || n.includes("female") || n.includes("susan") || n.includes("zira") || n.includes("samantha")) return "female";
  if (n.includes("david") || n.includes("male") || n.includes("daniel") || n.includes("alex")) return "male";
  return "unknown";
}

function pickVoiceByGender(voices, gender) {
  if (gender === "auto") return voices[0] || null;
  const filtered = voices.filter(v => inferGenderFromVoiceName(v.name) === gender);
  return filtered[0] || voices[0] || null;
}

// ----------- Speech Synthesis Setup -----------
let availableVoices = [];

function loadVoices() {
  availableVoices = window.speechSynthesis.getVoices().sort((a,b) => (a.name > b.name ? 1 : -1));
  voiceSelect.innerHTML = "";
  availableVoices.forEach((v, idx) => {
    const opt = document.createElement("option");
    opt.value = v.voiceURI || idx;
    opt.textContent = `${v.name} (${v.lang})`;
    opt.dataset.name = v.name;
    voiceSelect.appendChild(opt);
  });

  // Set default voice based on gender quick pick
  const selectedGender = document.querySelector('input[name="gender"]:checked').value;
  const defaultVoice = pickVoiceByGender(availableVoices, selectedGender);
  if (defaultVoice) {
    selectedVoice = defaultVoice;
    const i = availableVoices.findIndex(v => v.name === defaultVoice.name);
    if (i >= 0) voiceSelect.selectedIndex = i;
  }
}

window.speechSynthesis.onvoiceschanged = () => {
  loadVoices();
};

// Initial call (some browsers need an initial request)
setTimeout(loadVoices, 200);

// Refresh voices button (useful if voices load late)
refreshVoicesBtn.addEventListener("click", () => {
  loadVoices();
});

// Gender radio changes voice auto-pick
genderRadios.forEach(r => {
  r.addEventListener("change", () => {
    const gender = document.querySelector('input[name="gender"]:checked').value;
    const pick = pickVoiceByGender(availableVoices, gender);
    if (pick) {
      selectedVoice = pick;
      const i = availableVoices.findIndex(v => v.name === pick.name);
      if (i >= 0) voiceSelect.selectedIndex = i;
    }
  });
});

// Voice dropdown selection
voiceSelect.addEventListener("change", () => {
  const opt = voiceSelect.options[voiceSelect.selectedIndex];
  const name = opt.dataset.name;
  selectedVoice = availableVoices.find(v => v.name === name) || null;
});

// Rate/pitch/volume UI
function updateSliderLabels() {
  rateVal.textContent = rate.value;
  pitchVal.textContent = pitch.value;
  volumeVal.textContent = volume.value;
}
[rate, pitch, volume].forEach(el => el.addEventListener("input", updateSliderLabels));
updateSliderLabels();

// ----------- File Upload -----------
fileInput.addEventListener("change", () => {
  uploadBtn.disabled = !fileInput.files.length;
});

uploadBtn.addEventListener("click", async () => {
  if (!fileInput.files.length) return;
  setStatus("Uploading & extracting text…");
  preparedChunks = [];
  currentIndex = 0;
  speaking = false; paused = false; currentUtterance = null;
  updateControls();
  setProgress(0);
  nowReading.classList.add("hidden");
  nowReading.textContent = "";

  const data = new FormData();
  data.append("file", fileInput.files[0]);

  try {
    const res = await fetch("/api/upload", {
      method: "POST",
      body: data
    });
    const json = await res.json();
    if (!json.ok) {
      setStatus(json.error || "Failed to prepare PDF", false);
      return;
    }
    preparedChunks = json.chunks;
    setStatus(`Prepared "${json.filename}". Detected ${json.chunk_count} chunks. Ready to read.`);
    playBtn.disabled = false;
    updateControls();

    // Pre-populate preview
    if (preparedChunks.length) {
      nowReading.classList.remove("hidden");
      nowReading.textContent = splitPreviewText(preparedChunks[0], 600);
    }
  } catch (e) {
    console.error(e);
    setStatus("Upload failed. Check server logs.", false);
  }
});

// ----------- Playback -----------
function speakNext() {
  if (currentIndex >= preparedChunks.length) {
    speaking = false;
    paused = false;
    updateControls();
    setProgress(100);
    return;
  }

  const txt = preparedChunks[currentIndex];
  nowReading.classList.remove("hidden");
  nowReading.textContent = txt;

  const u = new SpeechSynthesisUtterance(txt);
  u.rate = parseFloat(rate.value);
  u.pitch = parseFloat(pitch.value);
  u.volume = parseFloat(volume.value);
  if (selectedVoice) u.voice = selectedVoice;

  u.onstart = () => {
    speaking = true;
    paused = false;
    updateControls();
    setProgress((currentIndex / preparedChunks.length) * 100);
  };

  u.onend = () => {
    if (!paused) {
      currentIndex++;
      setProgress((currentIndex / preparedChunks.length) * 100);
      speakNext();
    }
  };

  u.onerror = (e) => {
    console.error("Speech error", e);
    // skip this chunk if error, continue
    currentIndex++;
    speakNext();
  };

  currentUtterance = u;
  window.speechSynthesis.speak(u);
}

playBtn.addEventListener("click", () => {
  if (preparedChunks.length === 0) return;
  if (speaking) return;

  currentIndex = 0;
  speakNext();
});

pauseBtn.addEventListener("click", () => {
  if (!speaking || paused) return;
  window.speechSynthesis.pause();
  paused = true;
  updateControls();
});

resumeBtn.addEventListener("click", () => {
  if (!speaking || !paused) return;
  window.speechSynthesis.resume();
  paused = false;
  updateControls();
});

stopBtn.addEventListener("click", () => {
  window.speechSynthesis.cancel();
  speaking = false;
  paused = false;
  currentIndex = 0;
  updateControls();
  setProgress(0);
});
