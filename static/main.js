const PRIZE_URL = 'https://raw.githubusercontent.com/swes0123/Taiwan-Receipt-Lottery/master/prize.json';
const fallbackProxy = 'https://api.allorigins.win/raw?url=';

const defaultPrizeData = {
  special: '56983970',
  grand: '12345678',
  first: ['56781234', '98765432', '24681357'],
  second: [],
  third: [],
  fourth: [],
  fifth: [],
  sixth: [],
  seventh: []
};

let prizeNumbers = defaultPrizeData;
let ocrWorker = null;
let chart = null;
let stream = null;

const video = document.getElementById('video');
const startCameraButton = document.getElementById('startCamera');
const captureButton = document.getElementById('capturePhoto');
const fileInput = document.getElementById('fileInput');
const statusText = document.getElementById('statusText');
const detectedText = document.getElementById('detectedText');
const resultText = document.getElementById('resultText');
const prizeList = document.getElementById('prizeList');
const chartCanvas = document.getElementById('resultChart');
const snapshotCanvas = document.getElementById('snapshotCanvas');

async function fetchPrizeData() {
  try {
    const response = await fetch(fallbackProxy + encodeURIComponent(PRIZE_URL));
    if (!response.ok) throw new Error('網路回應錯誤');

    const data = await response.json();
    if (!data || !data.data) throw new Error('中獎資料格式不正確');
    prizeNumbers = data.data;
    statusText.textContent = '已自動取得最新中獎號碼。';
  } catch (error) {
    console.warn('中獎號碼更新失敗：', error);
    prizeNumbers = defaultPrizeData;
    statusText.textContent = '無法取得線上中獎號碼，使用本地預設資料。';
  }

  renderPrizeNumbers();
}

function renderPrizeNumbers() {
  prizeList.innerHTML = `
    <div><strong>特別獎：</strong>${prizeNumbers.special || '無'}</div>
    <div><strong>特獎：</strong>${prizeNumbers.grand || '無'}</div>
    <div><strong>頭獎：</strong>${prizeNumbers.first.length ? prizeNumbers.first.join(', ') : '無'}</div>
    <div><strong>增開六獎：</strong>${prizeNumbers.seventh.length ? prizeNumbers.seventh.join(', ') : '無'}</div>
  `;
}

async function initOCR() {
  statusText.textContent = '正在初始化 OCR 引擎，請稍候...';
  ocrWorker = Tesseract.createWorker({
    logger: (message) => {
      if (message.status && message.progress !== undefined) {
        statusText.textContent = `${message.status} (${Math.round(message.progress * 100)}%)`;
      }
    }
  });
  await ocrWorker.load();
  await ocrWorker.loadLanguage('eng');
  await ocrWorker.initialize('eng');
  await ocrWorker.setParameters({ tessedit_char_whitelist: '0123456789' });
  statusText.textContent = 'OCR 引擎已準備完成，可以開始拍照或上傳圖片。';
}

async function startCamera() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: true });
    video.srcObject = stream;
    video.play();
    statusText.textContent = '攝影機已啟用，請將發票對準鏡頭。';
  } catch (error) {
    console.error('啟用攝影機失敗', error);
    statusText.textContent = '無法啟用攝影機，請檢查權限或硬體。';
  }
}

async function capturePhoto() {
  if (!video.srcObject) {
    statusText.textContent = '請先啟用攝影機。';
    return;
  }

  snapshotCanvas.width = video.videoWidth;
  snapshotCanvas.height = video.videoHeight;
  const context = snapshotCanvas.getContext('2d');
  context.drawImage(video, 0, 0, snapshotCanvas.width, snapshotCanvas.height);
  await processImage(snapshotCanvas);
}

async function handleFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = async () => {
    const image = new Image();
    image.onload = async () => {
      snapshotCanvas.width = image.width;
      snapshotCanvas.height = image.height;
      const context = snapshotCanvas.getContext('2d');
      context.drawImage(image, 0, 0);
      await processImage(snapshotCanvas);
    };
    image.src = reader.result;
  };
  reader.readAsDataURL(file);
}

function extractEightDigitNumbers(text) {
  const matches = text.match(/\b\d{8}\b/g) || [];
  return [...new Set(matches)];
}

function judgeNumber(number) {
  if (number === prizeNumbers.special) return '特別獎（200 萬）';
  if (number === prizeNumbers.grand) return '特獎（200 萬）';

  for (const first of prizeNumbers.first) {
    if (number === first) return '頭獎（20 萬）';
    if (number.slice(-7) === first.slice(-7)) return '二獎（4 萬）';
    if (number.slice(-6) === first.slice(-6)) return '三獎（1 萬）';
    if (number.slice(-5) === first.slice(-5)) return '四獎（4,000 元）';
    if (number.slice(-4) === first.slice(-4)) return '五獎（1,000 元）';
    if (number.slice(-3) === first.slice(-3)) return '六獎（200 元）';
  }

  if (prizeNumbers.seventh.includes(number)) return '增開六獎（200 元）';
  return '未中獎';
}

function renderResult(numbers, resultLines) {
  detectedText.textContent = numbers.length ? numbers.join(', ') : '未偵測到 8 碼號碼。';
  resultText.textContent = resultLines.length ? resultLines.join('\n') : '未偵測到可對獎號碼。';
}

function renderChart(winCount, totalCount) {
  const loseCount = Math.max(totalCount - winCount, 0);
  const data = {
    labels: [`中獎 (${winCount})`, `未中獎 (${loseCount})`],
    datasets: [{
      data: [winCount, loseCount],
      backgroundColor: ['#22c55e', '#ef4444']
    }]
  };

  if (!chart) {
    chart = new Chart(chartCanvas.getContext('2d'), {
      type: 'pie',
      data,
      options: {
        plugins: {
          legend: { position: 'bottom' }
        }
      }
    });
  } else {
    chart.data = data;
    chart.update();
  }
}

async function processImage(source) {
  if (!ocrWorker) {
    statusText.textContent = 'OCR 引擎尚未準備好，請稍候。';
    return;
  }

  statusText.textContent = '正在辨識發票文字，請稍候...';

  try {
    const result = await ocrWorker.recognize(source);
    const text = result.data.text;
    const numbers = extractEightDigitNumbers(text);
    const resultLines = numbers.map((num) => `${num} → ${judgeNumber(num)}`);

    renderResult(numbers, resultLines);
    renderChart(numbers.filter((num) => judgeNumber(num) !== '未中獎').length, numbers.length);
    statusText.textContent = '辨識完成。';
  } catch (error) {
    console.error('OCR 失敗：', error);
    statusText.textContent = '辨識失敗，請重試或上傳更清晰的圖片。';
  }
}

window.addEventListener('DOMContentLoaded', async () => {
  await fetchPrizeData();
  await initOCR();
  captureButton.addEventListener('click', capturePhoto);
  startCameraButton.addEventListener('click', startCamera);
  fileInput.addEventListener('change', handleFileUpload);
  renderChart(0, 0);
});

window.addEventListener('beforeunload', async () => {
  if (ocrWorker) await ocrWorker.terminate();
  if (stream) {
    stream.getTracks().forEach((track) => track.stop());
  }
});
