document.addEventListener('DOMContentLoaded', () => {
    const calendarGrid = document.getElementById('calendar-grid');
    const currentMonthDisplay = document.getElementById('current-month-display');
    const prevMonthBtn = document.getElementById('prev-month');
    const nextMonthBtn = document.getElementById('next-month');
    const loadingOverlay = document.getElementById('loading');
    
    const mealModal = document.getElementById('meal-modal');
    const closeModalBtn = document.getElementById('close-modal');
    const modalDate = document.getElementById('modal-date');
    const modalMenu = document.getElementById('modal-menu');
    const modalCal = document.getElementById('modal-cal');
    const modalNutrition = document.getElementById('modal-nutrition');

    // State
    let currentDate = new Date();
    let mealsData = {}; // Format: { "YYYYMMDD": mealObject }

    // Constants for API
    const ATPT_OFCDC_SC_CODE = 'B10';
    const SD_SCHUL_CODE = '7010703';

    // Format Date to YYYYMMDD
    const formatDateStr = (date) => {
        const y = date.getFullYear();
        const m = String(date.getMonth() + 1).padStart(2, '0');
        const d = String(date.getDate()).padStart(2, '0');
        return `${y}${m}${d}`;
    };

    // Format for display
    const formatDisplayDate = (dateStr) => {
        const y = dateStr.slice(0, 4);
        const m = dateStr.slice(4, 6);
        const d = dateStr.slice(6, 8);
        const dateObj = new Date(y, parseInt(m) - 1, d);
        const days = ['일', '월', '화', '수', '목', '금', '토'];
        const dayName = days[dateObj.getDay()];
        return `${y}년 ${parseInt(m)}월 ${parseInt(d)}일 (${dayName})`;
    };

    // Clean up HTML tags (e.g., remove <br/> or keep them)
    const formatMultiline = (str) => {
        if (!str) return '';
        return str.replace(/<br\/>/g, '<br>');
    };

    // Fetch Meals Data
    const fetchMeals = async (year, month) => {
        // Calculate start and end dates of the month
        const startDate = new Date(year, month, 1);
        const endDate = new Date(year, month + 1, 0);
        
        const startYMD = formatDateStr(startDate);
        const endYMD = formatDateStr(endDate);
        
        const url = `https://open.neis.go.kr/hub/mealServiceDietInfo?Type=json&ATPT_OFCDC_SC_CODE=${ATPT_OFCDC_SC_CODE}&SD_SCHUL_CODE=${SD_SCHUL_CODE}&MLSV_FROM_YMD=${startYMD}&MLSV_TO_YMD=${endYMD}`;
        
        loadingOverlay.classList.add('active');
        try {
            const response = await fetch(url);
            const data = await response.json();
            
            mealsData = {}; // Clear previous data
            
            if (data.mealServiceDietInfo) {
                const rows = data.mealServiceDietInfo[1].row;
                rows.forEach(meal => {
                    // Only get lunch (MMEAL_SC_CODE === '2' usually means lunch, but we can store all or just use the date)
                    // If multiple meals exist per day, we might need an array. Assuming one main meal per day for now, or just storing the first one.
                    const date = meal.MLSV_YMD;
                    if (!mealsData[date]) {
                        mealsData[date] = [];
                    }
                    mealsData[date].push(meal);
                });
            }
        } catch (error) {
            console.error('Error fetching meals:', error);
            // Ignore error visually, maybe just show empty calendar
        } finally {
            loadingOverlay.classList.remove('active');
        }
    };

    // Render Calendar
    const renderCalendar = async () => {
        const year = currentDate.getFullYear();
        const month = currentDate.getMonth();
        
        currentMonthDisplay.textContent = `${year}년 ${month + 1}월`;
        
        await fetchMeals(year, month);
        
        calendarGrid.innerHTML = '';
        
        const firstDay = new Date(year, month, 1).getDay();
        const daysInMonth = new Date(year, month + 1, 0).getDate();
        
        const today = new Date();
        const isCurrentMonth = today.getFullYear() === year && today.getMonth() === month;
        const currentDay = today.getDate();

        // Previous month padding cells
        for (let i = 0; i < firstDay; i++) {
            const cell = document.createElement('div');
            cell.className = 'day-cell empty';
            calendarGrid.appendChild(cell);
        }

        // Days of current month
        for (let d = 1; d <= daysInMonth; d++) {
            const cell = document.createElement('div');
            cell.className = 'day-cell';
            
            if (isCurrentMonth && d === currentDay) {
                cell.classList.add('today');
            }
            
            const numDiv = document.createElement('div');
            numDiv.className = 'day-number';
            numDiv.textContent = d;
            
            // Highlight Sunday/Saturday colors based on column
            const dayOfWeek = (firstDay + d - 1) % 7;
            if (dayOfWeek === 0) numDiv.style.color = '#ef4444'; // Sun
            else if (dayOfWeek === 6) numDiv.style.color = '#3b82f6'; // Sat
            
            cell.appendChild(numDiv);

            const dateStr = formatDateStr(new Date(year, month, d));
            
            // Add meal badges
            if (mealsData[dateStr]) {
                mealsData[dateStr].forEach(meal => {
                    const badge = document.createElement('div');
                    badge.className = 'meal-badge';
                    
                    // Simple text extraction (removing allergy info in parentheses for cleaner badge view)
                    const cleanMenu = meal.DDISH_NM.replace(/<br\/>/g, ' ').replace(/\([^)]*\)/g, '').trim();
                    badge.textContent = cleanMenu || '급식 정보';
                    
                    badge.addEventListener('click', () => openModal(meal));
                    cell.appendChild(badge);
                });
            }

            calendarGrid.appendChild(cell);
        }

        // Next month padding cells
        const totalCells = firstDay + daysInMonth;
        const remainingCells = 7 - (totalCells % 7);
        if (remainingCells < 7) {
            for (let i = 0; i < remainingCells; i++) {
                const cell = document.createElement('div');
                cell.className = 'day-cell empty';
                calendarGrid.appendChild(cell);
            }
        }
    };

    // Modal Logic
    const openModal = (meal) => {
        modalDate.textContent = formatDisplayDate(meal.MLSV_YMD);
        
        // Clean up menu format
        modalMenu.innerHTML = formatMultiline(meal.DDISH_NM);
        modalCal.innerHTML = meal.CAL_INFO;
        modalNutrition.innerHTML = formatMultiline(meal.NTR_INFO);
        
        mealModal.classList.add('active');
    };

    const closeModal = () => {
        mealModal.classList.remove('active');
    };

    closeModalBtn.addEventListener('click', closeModal);
    mealModal.addEventListener('click', (e) => {
        if (e.target === mealModal) closeModal();
    });

    // Navigation
    prevMonthBtn.addEventListener('click', () => {
        currentDate.setMonth(currentDate.getMonth() - 1);
        renderCalendar();
    });

    nextMonthBtn.addEventListener('click', () => {
        currentDate.setMonth(currentDate.getMonth() + 1);
        renderCalendar();
    });

    // Initialize
    renderCalendar();
});
