"use strict";

const state = {
  convertedText: "",
  busy: false,
};

const elements = {
  apiStatus: document.getElementById("apiStatus"),
  sampleSelect: document.getElementById("sampleSelect"),
  sourceText: document.getElementById("sourceText"),
  charCount: document.getElementById("charCount"),
  convertButton: document.getElementById("convertButton"),
  resetButton: document.getElementById("resetButton"),
  errorMessage: document.getElementById("errorMessage"),
  loadingMessage: document.getElementById("loadingMessage"),
  copyButton: document.getElementById("copyButton"),
  downloadButton: document.getElementById("downloadButton"),
  copyMessage: document.getElementById("copyMessage"),
  sampleSource: document.getElementById("sampleSource"),
  originalText: document.getElementById("originalText"),
  convertedText: document.getElementById("convertedText"),
  originalChars: document.getElementById("originalChars"),
  originalSentences: document.getElementById("originalSentences"),
  originalAverage: document.getElementById("originalAverage"),
  convertedChars: document.getElementById("convertedChars"),
  convertedSentences: document.getElementById("convertedSentences"),
  convertedAverage: document.getElementById("convertedAverage")
};

async function loadStatus() {
  try {
    const response = await fetch("/api/status");
    const data = await response.json();
    elements.apiStatus.className = "status";
    if (data.status === "connected") {
      elements.apiStatus.classList.add("connected");
    } else if (data.status === "not_configured") {
      elements.apiStatus.classList.add("not-configured");
    } else {
      elements.apiStatus.classList.add("failed");
    }
    elements.apiStatus.textContent = data.status === "connected"
      ? "연결 성공"
      : data.status === "not_configured"
        ? "API 키 미설정"
        : "연결 실패";
    elements.apiStatus.title = data.message || "";
  } catch {
    elements.apiStatus.className = "status failed";
    elements.apiStatus.textContent = "연결 실패";
  }
}

async function loadSamples() {
  try {
    const response = await fetch("/api/samples");
    const data = await response.json();
    if (!response.ok || !data.success) throw new Error();
    data.samples.forEach((sample) => {
      const option = document.createElement("option");
      option.value = sample.sample_id;
      option.textContent = `[${sample.category}] ${sample.title}`;
      option.dataset.text = sample.original_text;
      option.dataset.source = sample.source;
      elements.sampleSelect.appendChild(option);
    });
  } catch {
    showError("샘플 목록을 불러오지 못했습니다.");
  }
}

function showError(message) {
  elements.errorMessage.textContent = message;
  elements.errorMessage.hidden = false;
}

function clearError() {
  elements.errorMessage.hidden = true;
  elements.errorMessage.textContent = "";
}

function updateCharCount() {
  const count = elements.sourceText.value.length;
  elements.charCount.textContent = `${count.toLocaleString("ko-KR")} / 12,000자`;
  if (!state.busy) {
    const text = elements.sourceText.value;
    elements.originalText.textContent = text || "원문을 입력하면 여기에 문서 내용이 표시됩니다.";
    if (text) {
      const sentences = countTextSentences(text);
      elements.originalChars.textContent = text.length.toLocaleString("ko-KR");
      elements.originalSentences.textContent = sentences.toLocaleString("ko-KR");
      const noSpaceLength = text.replace(/\s/g, "").length;
      elements.originalAverage.textContent = sentences ? (noSpaceLength / sentences).toFixed(1) : "-";
    } else {
      elements.originalChars.textContent = "-";
      elements.originalSentences.textContent = "-";
      elements.originalAverage.textContent = "-";
    }
  }
}

function countTextSentences(text) {
  const parts = text.trim().split(/[.!?。！？\n]+/);
  const count = parts.filter((part) => part.trim()).length;
  return count || (text.trim() ? 1 : 0);
}

function clearConvertedResult() {
  state.convertedText = "";
  elements.convertedText.textContent = "AI 변환 결과가 여기에 표시됩니다.";
  elements.convertedChars.textContent = "-";
  elements.convertedSentences.textContent = "-";
  elements.convertedAverage.textContent = "-";
  elements.copyButton.disabled = true;
  elements.downloadButton.disabled = true;
  document.getElementById("analysisEmpty").hidden = false;
  document.getElementById("analysisCharts").hidden = true;
  document.getElementById("preservationEmpty").hidden = false;
  document.getElementById("preservationResults").hidden = true;
  elements.copyMessage.hidden = true;
}

elements.sourceText.addEventListener("input", () => {
  updateCharCount();
  clearConvertedResult();
});

elements.sampleSelect.addEventListener("change", () => {
  const option = elements.sampleSelect.options[elements.sampleSelect.selectedIndex];
  if (!option || !option.dataset.text) {
    elements.sampleSource.hidden = true;
    elements.sampleSource.textContent = "";
    return;
  }
  elements.sourceText.value = option.dataset.text;
  elements.sampleSource.textContent = `자료 출처 표시: ${option.dataset.source || "출처 없음"}`;
  elements.sampleSource.hidden = false;
  updateCharCount();
  clearConvertedResult();
});

elements.resetButton.addEventListener("click", () => {
  if (elements.sourceText.value && !window.confirm("입력한 원문과 변환 결과를 모두 초기화할까요?")) return;
  elements.sampleSelect.value = "";
  elements.sourceText.value = "";
  elements.sampleSource.hidden = true;
  elements.sampleSource.textContent = "";
  elements.originalText.textContent = "원문을 입력하면 여기에 문서 내용이 표시됩니다.";
  elements.originalChars.textContent = "-";
  elements.originalSentences.textContent = "-";
  elements.originalAverage.textContent = "-";
  clearError();
  clearConvertedResult();
  updateCharCount();
});

document.querySelectorAll(".font-button").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".font-button").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    const scale = button.dataset.size === "small" ? "0.9" : button.dataset.size === "large" ? "1.12" : "1";
    document.documentElement.style.setProperty("--font-scale", scale);
  });
});

function setBusy(busy) {
  state.busy = busy;
  elements.convertButton.disabled = busy;
  elements.sourceText.disabled = busy;
  elements.sampleSelect.disabled = busy;
  elements.loadingMessage.hidden = !busy;
}

elements.convertButton.addEventListener("click", convertText);

async function convertText() {
  const text = elements.sourceText.value.trim();
  clearError();
  if (!text) {
    showError("변환할 원문을 입력해 주세요.");
    elements.sourceText.focus();
    return;
  }
  if (text.length > 12000) {
    showError("원문은 최대 12,000자까지 입력할 수 있습니다.");
    return;
  }

  setBusy(true);
  elements.convertedText.textContent = "공공정보를 이해하기 쉬운 표현으로 바꾸고 있습니다.";
  clearConvertedResult();
  elements.convertedText.textContent = "공공정보를 이해하기 쉬운 표현으로 바꾸고 있습니다.";

  try {
    const response = await fetch("/api/convert", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    const data = await response.json();
    if (!response.ok || !data.success) throw new Error(data.error || "변환에 실패했습니다.");

    state.convertedText = data.converted;
    elements.originalText.textContent = data.original;
    elements.convertedText.textContent = data.converted;
    elements.originalChars.textContent = data.original_analysis.character_count.toLocaleString("ko-KR");
    elements.originalSentences.textContent = data.original_analysis.sentence_count.toLocaleString("ko-KR");
    elements.originalAverage.textContent = data.original_analysis.average_sentence_length.toLocaleString("ko-KR");
    elements.convertedChars.textContent = data.converted_analysis.character_count.toLocaleString("ko-KR");
    elements.convertedSentences.textContent = data.converted_analysis.sentence_count.toLocaleString("ko-KR");
    elements.convertedAverage.textContent = data.converted_analysis.average_sentence_length.toLocaleString("ko-KR");
    elements.copyButton.disabled = false;
    elements.downloadButton.disabled = false;
    renderCharts(data.original_analysis, data.converted_analysis);
    renderPreservation(data.preservation);
  } catch (error) {
    elements.convertedText.textContent = "AI 변환 결과가 여기에 표시됩니다.";
    showError(error.message || "변환 중 오류가 발생했습니다.");
  } finally {
    setBusy(false);
  }
}

function chartRow(label, value, max, converted, suffix) {
  const width = max > 0 ? Math.max(2, (value / max) * 100) : 2;
  const row = document.createElement("div");
  row.className = `bar-row${converted ? " converted" : ""}`;
  const labelEl = document.createElement("span");
  labelEl.className = "bar-label";
  labelEl.textContent = label;
  const track = document.createElement("div");
  track.className = "bar-track";
  const fill = document.createElement("div");
  fill.className = "bar-fill";
  fill.style.width = `${width}%`;
  const valueEl = document.createElement("span");
  valueEl.className = "bar-value";
  valueEl.textContent = `${value}${suffix}`;
  track.appendChild(fill);
  row.append(labelEl, track, valueEl);
  return row;
}

function renderCharts(original, converted) {
  document.getElementById("analysisEmpty").hidden = true;
  document.getElementById("analysisCharts").hidden = false;

  const charChart = document.getElementById("charChart");
  const sentenceChart = document.getElementById("sentenceChart");
  const termChart = document.getElementById("termChart");
  charChart.replaceChildren();
  sentenceChart.replaceChildren();
  termChart.replaceChildren();

  let max = Math.max(original.character_count, converted.character_count, 1);
  charChart.append(chartRow("원문", original.character_count, max, false, "자"), chartRow("변환문", converted.character_count, max, true, "자"));

  max = Math.max(original.average_sentence_length, converted.average_sentence_length, 1);
  sentenceChart.append(chartRow("원문", original.average_sentence_length, max, false, "자"), chartRow("변환문", converted.average_sentence_length, max, true, "자"));

  max = Math.max(original.difficult_term_ratio, converted.difficult_term_ratio, 1);
  termChart.append(chartRow("원문", original.difficult_term_ratio, max, false, "%"), chartRow("변환문", converted.difficult_term_ratio, max, true, "%"));
}

function renderPreservation(preservation) {
  const empty = document.getElementById("preservationEmpty");
  const container = document.getElementById("preservationResults");
  container.replaceChildren();
  empty.hidden = true;
  container.hidden = false;

  preservation.categories.forEach((item) => {
    const card = document.createElement("article");
    card.className = "preservation-card";
    const title = document.createElement("h3");
    title.textContent = item.category;
    card.appendChild(title);

    if (item.confirmed.length) {
      const confirmed = document.createElement("p");
      confirmed.className = "confirmed";
      confirmed.textContent = `확인됨: ${item.confirmed.join(", ")}`;
      card.appendChild(confirmed);
    }
    if (item.missing.length) {
      const missing = document.createElement("p");
      missing.className = "missing";
      missing.textContent = `확인 필요: ${item.missing.join(", ")}`;
      card.appendChild(missing);
    }
    if (!item.confirmed.length && !item.missing.length) {
      const none = document.createElement("p");
      none.textContent = "원문에서 해당 항목을 찾지 못했습니다.";
      card.appendChild(none);
    }
    container.appendChild(card);
  });
}

elements.copyButton.addEventListener("click", async () => {
  if (!state.convertedText) return;
  try {
    await navigator.clipboard.writeText(state.convertedText);
    elements.copyMessage.textContent = "변환문을 클립보드에 복사했습니다.";
  } catch {
    elements.copyMessage.textContent = "복사에 실패했습니다. 브라우저의 클립보드 권한을 확인해 주세요.";
  }
  elements.copyMessage.hidden = false;
});

elements.downloadButton.addEventListener("click", () => {
  if (!state.convertedText) return;
  const blob = new Blob([state.convertedText], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "easy_text_result.txt";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
});

loadStatus();
loadSamples();
