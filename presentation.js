// presentation.js - VERSION AVEC LOGIQUE POINTEUR LASER CORRECTE

document.addEventListener('DOMContentLoaded', () => {
    "use strict";

    console.log("DOM Loaded. Initializing presentation script...");

    // --- Global Variables & DOM References --- //
    const presentationContainer = document.getElementById("presentation-container");
    const fullscreenButton = document.getElementById("fullscreen-button");
    const thumbnailMenuOverlay = document.getElementById("thumbnail-menu-overlay");
    const thumbnailGrid = document.querySelector(".thumbnail-grid");
    const closeThumbnailButton = document.getElementById("close-thumbnail-menu");
    const swiperElement = document.querySelector(".swiper");
    // Le pointeur laser sera créé dynamiquement
    // --------------------------------------

    let swiperInstance = null;
    let laserPointer = null;
    let resizeTimeoutId;
    let isUpdatingPositions = false;

    // --- Critical Element Checks --- //
    if (!presentationContainer) { console.error("CRITICAL ERROR: #presentation-container not found."); alert("Error: Missing container."); return; }
    if (!thumbnailMenuOverlay || !thumbnailGrid || !closeThumbnailButton) { console.error("CRITICAL ERROR: Missing thumbnail elements."); alert("Error: Missing thumbnail elements."); return; }
    if (!swiperElement) { console.error("CRITICAL ERROR: .swiper element not found."); alert("Error: Missing swiper element."); return; }

    // --- Utility Functions --- //
    function updateVideoPositions(slideElement) {
        if (isUpdatingPositions) { return; }
        if (!slideElement || !presentationContainer || !swiperInstance || swiperInstance.destroyed) { console.error("updateVideoPositions: Missing elements or Swiper invalid."); return; }
        isUpdatingPositions = true;
        requestAnimationFrame(() => {
            try {
                if (!swiperInstance || swiperInstance.destroyed) { console.warn("updateVideoPositions (rAF): Swiper invalid."); return; }
                const slideIndex = slideElement.dataset.slideIndex ?? "unknown";
                const pdfPageWidthPtStr = slideElement.dataset.pdfPageWidth; const pdfPageHeightPtStr = slideElement.dataset.pdfPageHeight;
                if (!pdfPageWidthPtStr || !pdfPageHeightPtStr) { console.error(`Slide ${slideIndex}: Missing page dimensions.`); return; }
                const pdfPageWidthPt = parseFloat(pdfPageWidthPtStr); const pdfPageHeightPt = parseFloat(pdfPageHeightPtStr);
                if (isNaN(pdfPageWidthPt) || isNaN(pdfPageHeightPt) || pdfPageWidthPt <= 0 || pdfPageHeightPt <= 0) { console.error(`Slide ${slideIndex}: Invalid page dimensions.`); return; }
                const wrapperRect = presentationContainer.getBoundingClientRect();
                const currentWrapperWidthPx = wrapperRect.width; const currentWrapperHeightPx = wrapperRect.height;
                if (currentWrapperWidthPx <= 0 || currentWrapperHeightPx <= 0) { return; }
                const wrapperAspect = currentWrapperWidthPx / currentWrapperHeightPx; const pdfAspect = pdfPageWidthPt / pdfPageHeightPt;
                let scaleToFit = (wrapperAspect > pdfAspect) ? currentWrapperHeightPx / pdfPageHeightPt : currentWrapperWidthPx / pdfPageWidthPt;
                const scaledSlideWidth = pdfPageWidthPt * scaleToFit; const scaledSlideHeight = pdfPageHeightPt * scaleToFit;
                const slideOffsetX = (currentWrapperWidthPx - scaledSlideWidth) / 2; const slideOffsetY = (currentWrapperHeightPx - scaledSlideHeight) / 2;
                const videos = slideElement.querySelectorAll(".slide-video-overlay");
                videos.forEach((video, videoIndex) => {
                    const pdfLlxStr = video.dataset.pdfRectLlx; const pdfLlyStr = video.dataset.pdfRectLly; const pdfUrxStr = video.dataset.pdfRectUrx; const pdfUryStr = video.dataset.pdfRectUry;
                    if (!pdfLlxStr || !pdfLlyStr || !pdfUrxStr || !pdfUryStr) { console.error(`Video ${videoIndex} (slide ${slideIndex}): Missing rect data.`); return; }
                    const pdfLlx = parseFloat(pdfLlxStr); const pdfLly = parseFloat(pdfLlyStr); const pdfUrx = parseFloat(pdfUrxStr); const pdfUry = parseFloat(pdfUryStr);
                    if ([pdfLlx, pdfLly, pdfUrx, pdfUry].some(isNaN)) { console.error(`Video ${videoIndex} (slide ${slideIndex}): Invalid rect coords.`); return; }
                    const pdfVideoWidthPt = pdfUrx - pdfLlx; const pdfVideoHeightPt = pdfUry - pdfLly;
                    if (pdfVideoWidthPt <= 0 || pdfVideoHeightPt <= 0) { console.error(`Video ${videoIndex} (slide ${slideIndex}): Invalid video dimensions.`); return; }
                    const videoLeftPxRelative = pdfLlx * scaleToFit; const videoTopPxRelative = (pdfPageHeightPt - pdfUry) * scaleToFit;
                    const videoWidthPx = pdfVideoWidthPt * scaleToFit; const videoHeightPx = pdfVideoHeightPt * scaleToFit;
                    const videoLeftPxFinal = slideOffsetX + videoLeftPxRelative; const videoTopPxFinal = slideOffsetY + videoTopPxRelative;
                    if (videoWidthPx <= 0 || videoHeightPx <= 0 || !Number.isFinite(videoLeftPxFinal) || !Number.isFinite(videoTopPxFinal)) { console.error(`Video ${videoIndex} (slide ${slideIndex}): Invalid calculated style.`); return; }
                    video.style.left = `${videoLeftPxFinal}px`; video.style.top = `${videoTopPxFinal}px`; video.style.width = `${videoWidthPx}px`; video.style.height = `${videoHeightPx}px`;
                });
            } finally { isUpdatingPositions = false; }
        });
    }
    function handleSlideChange(swiper) { if (!swiper || swiper.destroyed || !swiper.slides || swiper.slides.length === 0) { console.warn("handleSlideChange: Swiper invalid/destroyed/empty."); return; } const activeSlide = swiper.slides[swiper.activeIndex]; const activeIndex = swiper.activeIndex; if (activeSlide) { requestAnimationFrame(() => updateVideoPositions(activeSlide)); } else { console.warn(`handleSlideChange: Active slide (index ${activeIndex}) not found.`); } swiper.slides.forEach((slide, index) => { const videos = slide.querySelectorAll("video.slide-video-overlay"); videos.forEach(videoElement => { if (index === activeIndex) { if (videoElement.hasAttribute("data-autoplay")) { const playPromise = videoElement.play(); if (playPromise !== undefined) { playPromise.catch(error => { if (error.name !== 'NotAllowedError') { console.warn(`Play failed ${videoElement.id}:`, error.message); } }); } } } else { if (!videoElement.paused) { videoElement.pause(); } if (videoElement.currentTime !== 0) { videoElement.currentTime = 0; } } }); }); }
    function toggleFullScreen() { const presentationContainer = document.getElementById("presentation-container"); const notInFullscreen = (!document.fullscreenElement && !document.mozFullScreenElement && !document.webkitFullscreenElement && !document.msFullscreenElement); if (notInFullscreen) { const element = presentationContainer; if (!element) return; if (element.requestFullscreen) { element.requestFullscreen().catch(err => console.error(`FS Error: ${err.message}`)); } else if (element.mozRequestFullScreen) { element.mozRequestFullScreen(); } else if (element.webkitRequestFullscreen) { element.webkitRequestFullscreen(); } else if (element.msRequestFullscreen) { element.msRequestFullscreen(); } } else { if (document.exitFullscreen) { document.exitFullscreen().catch(err => console.error(`Exit FS Error: ${err.message}`)); } else if (document.mozCancelFullScreen) { document.mozCancelFullScreen(); } else if (document.webkitExitFullscreen) { document.webkitExitFullscreen(); } else if (document.msExitFullscreen) { document.msExitFullscreen(); } } }
    function hideThumbnailMenu() { const overlay = document.getElementById("thumbnail-menu-overlay"); if (overlay) { overlay.classList.remove('visible'); console.log("Thumbs hidden."); } }
    function showThumbnailMenu() { if (swiperInstance && !swiperInstance.destroyed) { generateThumbnails(swiperInstance); } else { console.error("Cannot show thumbnails, swiper invalid."); if(thumbnailGrid) thumbnailGrid.innerHTML = '<p class="error-message">Error loading.</p>'; } const overlay = document.getElementById("thumbnail-menu-overlay"); if (overlay) { overlay.classList.add('visible'); console.log("Thumbs shown."); } }
    function toggleThumbnailMenu() { const overlay = document.getElementById("thumbnail-menu-overlay"); if (overlay) { const isGoingToBeVisible = !overlay.classList.contains('visible'); if (isGoingToBeVisible) { if (swiperInstance && !swiperInstance.destroyed) { generateThumbnails(swiperInstance); } else { console.error("Cannot show/gen thumbs, swiper invalid."); if(thumbnailGrid) thumbnailGrid.innerHTML = '<p class="error-message">Error loading.</p>'; } } overlay.classList.toggle('visible'); console.log(`Thumbs ${overlay.classList.contains('visible')?'shown':'hidden'}.`); } }
    function generateThumbnails(swiper) { if (!swiper || swiper.destroyed || !swiper.slides || !thumbnailGrid) { console.error("Cannot generate thumbnails: Swiper invalid or grid missing."); if (thumbnailGrid) thumbnailGrid.innerHTML = '<p class="error-message">Error loading.</p>'; return; } console.log("Generating thumbnails..."); thumbnailGrid.innerHTML = ''; swiper.slides.forEach((slide, index) => { const slideIndex = parseInt(slide.dataset.slideIndex ?? index, 10); const svgImgElement = slide.querySelector('img.slide-background-svg'); const svgUrl = svgImgElement?.src; const thumbItem = document.createElement('div'); thumbItem.classList.add('thumbnail-item'); thumbItem.dataset.gotoSlide = slideIndex; if (svgUrl) { const img = document.createElement('img'); img.src = svgUrl; img.alt = `Thumb ${slideIndex + 1}`; img.loading = 'lazy'; thumbItem.appendChild(img); } else { const fallback = document.createElement('span'); fallback.textContent = `Slide ${slideIndex + 1}`; fallback.style.cssText='font-size:0.8em;color:#666;'; thumbItem.appendChild(fallback); } const numSpan = document.createElement('span'); numSpan.classList.add('slide-number'); numSpan.textContent = slideIndex + 1; thumbItem.appendChild(numSpan); thumbItem.addEventListener('click', () => { const targetIndex = parseInt(thumbItem.dataset.gotoSlide, 10); if (!isNaN(targetIndex) && swiper && !swiper.destroyed) { console.log(`Thumb -> Slide ${targetIndex}`); swiper.slideTo(targetIndex); hideThumbnailMenu(); } }); thumbnailGrid.appendChild(thumbItem); }); const count = swiper.slides?.length ?? 0; console.log(`${count} thumbs generated.`); }

    /** Crée un nouveau pointeur laser */
    function createLaserPointer() {
        const laser = document.createElement('div');
        laser.className = 'laser-pointer';
        laser.style.cssText = `
            position: fixed !important;
            top: 0;
            left: 0;
            width: 6px;
            height: 6px;
            background-color: #ff0000;
            border-radius: 50%;
            border: 1px solid rgba(233, 147, 199, 0.5);
            box-shadow: 
                0 0 1px 1px #000000,
                0 0 2px 2px rgba(200, 89, 89, 0.2),
                0 0 4px 2px rgba(200, 89, 89, 0.2),
                0 0 8px 4px rgba(255, 0, 0, 0.3);
            pointer-events: none !important;
            transform: translate(-50%, -50%);
            z-index: 2147483647 !important;
            display: block;
            mix-blend-mode: difference;
            visibility: visible !important;
            opacity: 1 !important;
        `;
        return laser;
    }

    /** Met à jour la visibilité du pointeur laser */
    function updateLaserPointerVisibility() {
        const fullscreenElement = (
            document.fullscreenElement || document.webkitFullscreenElement ||
            document.mozFullScreenElement || document.msFullscreenElement
        );

        console.log(`DEBUG: Fullscreen change detected, element:`, fullscreenElement);

        // Supprimer l'ancien pointeur s'il existe
        if (laserPointer && laserPointer.parentNode) {
            laserPointer.parentNode.removeChild(laserPointer);
            laserPointer = null;
        }

        if (fullscreenElement) {
            // Créer un nouveau pointeur
            laserPointer = createLaserPointer();
            // L'ajouter directement à l'élément en plein écran
            fullscreenElement.appendChild(laserPointer);
            console.log('DEBUG: New laser pointer created and attached');
        }
    }

    /** Gère le mouvement de la souris pour le pointeur laser */
    function handleMouseMove(event) {
        if (laserPointer) {
            requestAnimationFrame(() => {
                if (laserPointer) {
                    const x = event.clientX;
                    const y = event.clientY;
                    laserPointer.style.top = `${y}px`;
                    laserPointer.style.left = `${x}px`;
                    console.log(`DEBUG: Laser moved to ${x},${y}`);
                }
            });
        }
    }
    // --- END Laser Pointer Functions ---

    /** Handles browser fullscreen change events. */
    function handleFullscreenChange() {
        // Pas besoin du log isFullscreen ici car updateLaserPointerVisibility le fait déjà
        console.log("DEBUG: handleFullscreenChange event triggered."); // LOG AJOUTÉ

        // Mettre à jour la visibilité du pointeur
        updateLaserPointerVisibility();

        // Mettre à jour Swiper après un délai
        setTimeout(() => {
            if (swiperInstance && !swiperInstance.destroyed) {
                swiperInstance.update();
                console.log("Swiper updated after fullscreen change timeout.");
                const currentSlide = swiperInstance.slides?.[swiperInstance.activeIndex];
                if (currentSlide) {
                    requestAnimationFrame(() => {
                        updateVideoPositions(currentSlide);
                        // console.log("Video positions recalc after fullscreen timeout."); // Moins utile maintenant
                    });
                }
            } else {
                console.warn("handleFullscreenChange timeout: Swiper instance invalid/destroyed.");
            }
        }, 300); // Garder le délai pour la mise à jour Swiper/vidéo
    }


    // --- Swiper Initialization --- //
    try {
        let swiperOptions = {
            direction: "horizontal", loop: false, speed: 0, watchSlidesProgress: true,
            slidesPerView: 1, observer: true, observeParents: true, observeSlideChildren: true,
            resizeObserver: true, keyboard: { enabled: false },
            on: {
                init: function (swiper) {
                     console.log("Swiper 'init' event fired.");
                     if (swiper && !swiper.destroyed) { swiper.update(); }
                     setTimeout(() => {
                         console.log("Executing Swiper init callback timeout...");
                         if (swiperInstance && !swiperInstance.destroyed && swiperInstance.slides && swiperInstance.slides.length > 0) {
                             console.log("Swiper instance valid in init timeout.");
                             const initialSlide = swiperInstance.slides[swiperInstance.activeIndex];
                             if (initialSlide) { updateVideoPositions(initialSlide); handleSlideChange(swiperInstance); generateThumbnails(swiperInstance); }
                             else { console.warn("Swiper init timeout: Could not get initial slide."); }
                         } else { console.warn("Swiper init timeout: Swiper instance/slides not ready."); }
                     }, 250);
                 },
                 slideChangeTransitionEnd: function (swiper) {
                      if (swiper && !swiper.destroyed) { handleSlideChange(swiper); }
                      else { console.warn("slideChangeTransitionEnd: Swiper invalid/destroyed."); }
                 },
                 resize: function (/* swiper */) {
                     clearTimeout(resizeTimeoutId);
                     resizeTimeoutId = setTimeout(() => {
                         console.log("Executing resize timeout...");
                         if (!swiperInstance || swiperInstance.destroyed || !swiperInstance.slides || swiperInstance.slides.length === 0) { console.warn("Resize timeout: Swiper invalid/empty."); return; }
                         const currentSlide = swiperInstance.slides[swiperInstance.activeIndex];
                         if (currentSlide) { updateVideoPositions(currentSlide); }
                         else { console.warn("Resize timeout: Active slide not found."); }
                     }, 250);
                 }
            },
        };

        swiperInstance = new Swiper(".swiper", swiperOptions);
        console.log("Swiper instance created.");
        if (swiperInstance && !swiperInstance.destroyed) { swiperInstance.update(); }

    } catch (error) {
        console.error("CRITICAL ERROR during Swiper initialization:", error);
        if (presentationContainer) { presentationContainer.innerHTML = '<p class="error-message">Error initializing.</p>'; }
        alert("Critical Error: Could not initialize slideshow.");
        return;
    }

    // --- Global Event Listeners --- //
    if (fullscreenButton) { fullscreenButton.addEventListener("click", toggleFullScreen); }

    // --- AJOUT/MODIF POINTEUR ---
    // Listeners pour le plein écran (appelle la fonction handleFullscreenChange modifiée)
    console.log("Adding fullscreen change listeners...");
    // --- Event Listeners ---
    window.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('fullscreenchange', updateLaserPointerVisibility);
    document.addEventListener('webkitfullscreenchange', updateLaserPointerVisibility);
    document.addEventListener('mozfullscreenchange', updateLaserPointerVisibility);
    document.addEventListener('MSFullscreenChange', updateLaserPointerVisibility);

    // Ajouter des écouteurs pour les vidéos
    document.querySelectorAll('video').forEach(video => {
        video.addEventListener('dblclick', () => {
            // Créer le pointeur avant de passer en plein écran
            if (laserPointer && laserPointer.parentNode) {
                laserPointer.parentNode.removeChild(laserPointer);
            }
            laserPointer = createLaserPointer();
            document.body.appendChild(laserPointer);
            
            // Passer en plein écran
            if (video.requestFullscreen) {
                video.requestFullscreen();
            } else if (video.webkitRequestFullscreen) {
                video.webkitRequestFullscreen();
            } else if (video.mozRequestFullScreen) {
                video.mozRequestFullScreen();
            } else if (video.msRequestFullscreen) {
                video.msRequestFullscreen();
            }
        });
    });

    // Ajouter les écouteurs d'événements sur toutes les vidéos existantes
    document.querySelectorAll('video').forEach(video => {
        video.addEventListener('fullscreenchange', handleFullscreenChange);
        video.addEventListener('webkitfullscreenchange', handleFullscreenChange);
        video.addEventListener('mozfullscreenchange', handleFullscreenChange);
        video.addEventListener('MSFullscreenChange', handleFullscreenChange);
    });

    // Observer les nouvelles vidéos ajoutées dynamiquement
    const videoObserver = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            mutation.addedNodes.forEach((node) => {
                if (node.nodeName === 'VIDEO') {
                    node.addEventListener('fullscreenchange', handleFullscreenChange);
                    node.addEventListener('webkitfullscreenchange', handleFullscreenChange);
                    node.addEventListener('mozfullscreenchange', handleFullscreenChange);
                    node.addEventListener('MSFullscreenChange', handleFullscreenChange);
                }
            });
        });
    });

    // Observer les changements dans tout le document
    videoObserver.observe(document.body, {
        childList: true,
        subtree: true
    });

    // Listener pour le mouvement de la souris
    console.log("Adding mousemove listener...");
    document.addEventListener("mousemove", handleMouseMove);
    // --- FIN AJOUT/MODIF POINTEUR ---

    // Keyboard listener
    document.addEventListener('keydown', (event) => { if (!swiperInstance || swiperInstance.destroyed || !swiperInstance.enabled) { return; } const targetTagName = event.target.tagName.toLowerCase(); if (['input', 'textarea', 'select'].includes(targetTagName)) { return; } const isMenuVisible = thumbnailMenuOverlay?.classList.contains('visible'); const isMenuKey = ['Escape', 'm', 'M'].includes(event.key); if (isMenuVisible && !isMenuKey) { return; } let shouldPreventDefault = true; switch (event.key) { case 'ArrowRight': case 'PageDown': case ' ': if (!event.shiftKey) { swiperInstance.slideNext(); } else { shouldPreventDefault = false; } break; case 'ArrowLeft': case 'PageUp': swiperInstance.slidePrev(); break; case 'Home': swiperInstance.slideTo(0); break; case 'End': if (swiperInstance.slides?.length > 0) { swiperInstance.slideTo(swiperInstance.slides.length - 1); } break; case 'f': case 'F': toggleFullScreen(); break; case 'm': case 'M': toggleThumbnailMenu(); break; case 'Escape': if (isMenuVisible) { hideThumbnailMenu(); } else { shouldPreventDefault = false; } break; default: shouldPreventDefault = false; break; } if (shouldPreventDefault) { event.preventDefault(); } });
    console.log("Keyboard event listener added.");

    // Thumbnail menu listeners
    if (thumbnailMenuOverlay) { thumbnailMenuOverlay.addEventListener('click', (event) => { if (event.target === thumbnailMenuOverlay) { hideThumbnailMenu(); } }); }
    if (closeThumbnailButton) { closeThumbnailButton.addEventListener('click', hideThumbnailMenu); }

    // Window load listener
    window.addEventListener("load", () => { console.log("Window 'load' event received."); setTimeout(() => { if (!swiperInstance || swiperInstance.destroyed || !swiperInstance.slides || swiperInstance.slides.length === 0) { console.warn("Window load timeout: Swiper invalid/empty."); return; } const currentSlide = swiperInstance.slides[swiperInstance.activeIndex]; if (currentSlide) { updateVideoPositions(currentSlide); } else { console.warn("Window load timeout: Active slide not found."); } }, 300); });

    // --- AJOUT/MODIF POINTEUR ---
    // Initial check for laser pointer visibility
    if(laserPointer) {
        console.log("Performing initial laser pointer visibility check...");
        updateLaserPointerVisibility(); // Set initial state (should be hidden)
    }
    // --- FIN AJOUT/MODIF POINTEUR ---

}); // End DOMContentLoaded listener
