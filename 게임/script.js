const ROWS = 8;
const COLS = 12;
const TARGET_SUM = 10;
const GAME_TIME = 120; // 2 minutes

const board = document.getElementById('game-board');
const scoreEl = document.getElementById('score');
const timerEl = document.getElementById('timer');
const startScreen = document.getElementById('start-screen');
const resultScreen = document.getElementById('result-screen');
const finalScoreEl = document.getElementById('final-score');
const restartBtn = document.getElementById('restart-btn');
const startBtn = document.getElementById('start-btn');
const gridWrapper = document.querySelector('.grid-wrapper');

let score = 0;
let timeLeft = GAME_TIME;
let timerInterval;
let cells = [];
let selectedCells = []; 
let isGameActive = false;

// Helpers for Special Types
function generateType() {
  const rand = Math.random();
  if (rand < 0.08) return 'bomb'; // 8% chance bomb
  if (rand < 0.15) return 'time'; // 7% chance time bonus
  return 'normal';
}

function applyTypeToCell(cellObj, targetType = null) {
  cellObj.type = targetType || generateType();
  const fruit = cellObj.element.querySelector('.fruit');
  
  // Clean classes
  fruit.className = 'fruit';
  const existingIcon = cellObj.element.querySelector('.special-icon');
  if (existingIcon) existingIcon.remove();
  
  if (cellObj.type === 'bomb') {
    fruit.classList.add('bomb');
    const icon = document.createElement('div');
    icon.classList.add('special-icon');
    icon.textContent = '💣';
    cellObj.element.appendChild(icon);
  } else if (cellObj.type === 'time') {
    fruit.classList.add('time');
    const icon = document.createElement('div');
    icon.classList.add('special-icon');
    icon.textContent = '⏰';
    cellObj.element.appendChild(icon);
  }
}

// Show animated floating text on board
function showFloatingText(text, x, y, color) {
  const el = document.createElement('div');
  el.className = 'floating-text';
  el.style.left = `${x}px`;
  el.style.top = `${y}px`;
  el.style.color = color;
  el.textContent = text;
  gridWrapper.appendChild(el);
  setTimeout(() => el.remove(), 1000);
}

// Initialize the board only
function initBoard() {
  board.innerHTML = '';
  cells = [];
  selectedCells = [];
  for (let r = 0; r < ROWS; r++) {
    for (let c = 0; c < COLS; c++) {
      createCell(r, c);
    }
  }
}

function createCell(row, col) {
  const cell = document.createElement('div');
  cell.classList.add('cell');
  cell.dataset.row = row;
  cell.dataset.col = col;
  
  const num = Math.floor(Math.random() * 9) + 1;
  cell.dataset.value = num;
  
  const fruit = document.createElement('div');
  fruit.classList.add('fruit');
  fruit.textContent = '🍌';
  
  const numberSpan = document.createElement('div');
  numberSpan.classList.add('number');
  numberSpan.textContent = num;
  
  cell.appendChild(fruit);
  cell.appendChild(numberSpan);
  
  const cellObj = { element: cell, row, col, value: num, cleared: false };
  applyTypeToCell(cellObj);
  
  cell.addEventListener('mousedown', () => handleCellClick(cellObj));
  
  board.appendChild(cell);
  cells.push(cellObj);
}

function handleCellClick(cellObj) {
  if (!isGameActive || cellObj.cleared) return;
  
  const index = selectedCells.indexOf(cellObj);
  
  if (index > -1) {
    selectedCells.splice(index, 1);
    cellObj.element.classList.remove('selected');
  } else {
    selectedCells.push(cellObj);
    cellObj.element.classList.add('selected');
  }
  
  checkSelection();
}

function checkSelection() {
  if (selectedCells.length === 0) return;
  
  const sum = selectedCells.reduce((acc, cell) => acc + cell.value, 0);
  
  if (sum === TARGET_SUM) {
    processMatch();
  } else if (sum > TARGET_SUM) {
    // Over 10 Penalty
    selectedCells.forEach(cellObj => {
      cellObj.element.classList.remove('selected');
      cellObj.element.classList.remove('shake');
      void cellObj.element.offsetWidth; 
      cellObj.element.classList.add('shake');
    });
    selectedCells = [];
  }
}

function processMatch() {
  let cellsToClear = new Set();
  let timeAdded = 0;
  let queue = [...selectedCells];
  
  // Add original selection
  selectedCells.forEach(c => cellsToClear.add(c));
  
  // Process special chains (BFS style for chain explosions)
  while (queue.length > 0) {
    const current = queue.shift();
    
    if (current.type === 'time') {
      timeAdded += 5;
    }
    
    if (current.type === 'bomb') {
      // Explode 3x3
      for (let r = current.row - 1; r <= current.row + 1; r++) {
        for (let c = current.col - 1; c <= current.col + 1; c++) {
          if (r >= 0 && r < ROWS && c >= 0 && c < COLS) {
            const adjacent = cells.find(x => x.row === r && x.col === c);
            if (adjacent && !adjacent.cleared && !cellsToClear.has(adjacent)) {
              cellsToClear.add(adjacent);
              // Chain reaction if the destroyed block is also a bomb/time
              if (adjacent.type === 'bomb' || adjacent.type === 'time') {
                queue.push(adjacent);
              }
            }
          }
        }
      }
    }
    
    // Disable it from multiple triggers
    current.type = 'normal'; 
  }
  
  // Handle Time Bonus
  if (timeAdded > 0) {
    timeLeft += timeAdded;
    timerEl.textContent = timeLeft;
    
    // Find center of screen or first time bomb position to show floating text
    const triggerCell = selectedCells[0];
    const rect = triggerCell.element.getBoundingClientRect();
    const wrapperRect = gridWrapper.getBoundingClientRect();
    showFloatingText(`+${timeAdded} SEC!`, rect.left - wrapperRect.left, rect.top - wrapperRect.top, '#4dd0e1');
  }
  
  // Handle Score (Combo for multiple explosive clears)
  let gainedScore = cellsToClear.size * 10;
  if (cellsToClear.size > selectedCells.length) {
    // Boom bonus!
    gainedScore += (cellsToClear.size - selectedCells.length) * 15;
    const triggerCell = selectedCells[0];
    const rect = triggerCell.element.getBoundingClientRect();
    const wrapperRect = gridWrapper.getBoundingClientRect();
    showFloatingText(`BOOM! +${gainedScore}`, rect.left - wrapperRect.left + 50, rect.top - wrapperRect.top, '#ff3333');
  }
  score += gainedScore;
  scoreEl.textContent = score;
  
  // Clear the cells visually
  const cellsArray = Array.from(cellsToClear);
  cellsArray.forEach(c => {
    c.cleared = true;
    c.element.classList.remove('selected');
    c.element.classList.add('cleared'); // Hides and shrinks
  });
  
  selectedCells = [];
  
  // Wait 1 second (1000ms delay as requested) then refill
  setTimeout(() => {
    if (!isGameActive) return; // Prevent bugs if game ends during wait
    cellsArray.forEach(c => {
      refillCell(c);
    });
  }, 1000);
}

function refillCell(cellObj) {
  const newNum = Math.floor(Math.random() * 9) + 1;
  cellObj.value = newNum;
  cellObj.element.dataset.value = newNum;
  
  const numberSpan = cellObj.element.querySelector('.number');
  numberSpan.textContent = newNum;
  
  applyTypeToCell(cellObj); // Roll for new special item
  
  // Re-enable interactions and Pop-in
  cellObj.cleared = false;
  cellObj.element.classList.remove('cleared', 'selected');
  
  cellObj.element.classList.remove('pop-in');
  void cellObj.element.offsetWidth; 
  cellObj.element.classList.add('pop-in');
}

function startGame() {
  isGameActive = true;
  score = 0;
  timeLeft = GAME_TIME;
  scoreEl.textContent = score;
  timerEl.textContent = timeLeft;
  
  startScreen.classList.remove('active');
  resultScreen.classList.remove('active');
  
  initBoard(); 
  
  clearInterval(timerInterval);
  timerInterval = setInterval(updateTimer, 1000);
}

function updateTimer() {
  timeLeft--;
  timerEl.textContent = timeLeft;
  if (timeLeft <= 0) {
    endGame();
  }
}

function endGame() {
  clearInterval(timerInterval);
  isGameActive = false;
  finalScoreEl.textContent = score;
  resultScreen.classList.add('active');
  selectedCells.forEach(c => c.element.classList.remove('selected'));
  selectedCells = [];
}

startBtn.addEventListener('click', startGame);
restartBtn.addEventListener('click', startGame);

initBoard();
