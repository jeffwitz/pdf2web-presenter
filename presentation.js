// presentation.js - VERSION WITH CORRECT LASER POINTER LOGIC

document.addEventListener('DOMContentLoaded', () => {
    "use strict";

    console.log("DOM Loaded. Initializing presentation script...");

    // --- Global Variables & DOM References --- //

/**
 * Generates the responsive list of slide numbers for mobile/small height.
 * Displays only numbers, no popover or image.
 */
function generateMinimalNumberList() {
    const numberList = document.querySelector('.thumbnail-number-list');
    const swiperElement = document.querySelector('.swiper');
    const thumbnailMenuOverlay = document.getElementById('thumbnail-menu-overlay');
    if (!numberList || !swiperElement) return;
    numberList.innerHTML = '';
    const slides = swiperElement.querySelectorAll('.swiper-slide');
    
    // --- Créer un popover UNIQUE qui sera réutilisé ---
    // Créer le conteneur une seule fois, directement dans le body
    const popover = document.createElement('div');
    popover.className = 'one-popover'; // Classe spéciale, pas mini-thumb-popover
    popover.style.position = 'fixed';
    popover.style.zIndex = '10000';
    popover.style.background = '#fff';
    popover.style.border = '1.5px solid #888';
    popover.style.borderRadius = '12px';
    popover.style.boxShadow = '0 8px 32px rgba(0,0,0,0.28)';
    popover.style.padding = '8px';
    popover.style.display = 'flex';
    popover.style.alignItems = 'center';
    popover.style.justifyContent = 'center';
    popover.style.minWidth = '120px';
    popover.style.maxWidth = '260px';
    popover.style.maxHeight = '180px';
    popover.style.pointerEvents = 'none'; // Crucial pour éviter le flicker
    popover.style.opacity = '0';  // Caché par défaut
    popover.style.transition = 'opacity 0.22s';
    // Cacher hors écran au début
    popover.style.left = '-9999px';
    popover.style.top = '-9999px';
    document.body.appendChild(popover);

    let popoverTimeout = null;
    let currentTarget = null;
    
    // Masquer le popover
    function hidePopover() {
        if (popoverTimeout) {
            clearTimeout(popoverTimeout);
            popoverTimeout = null;
        }
        // Ne pas supprimer l'élément, juste le déplacer hors écran
        popover.style.opacity = '0';
        // Après la transition, le déplacer hors écran
        setTimeout(() => {
            if (popover) {
                popover.style.left = '-9999px';
                popover.style.top = '-9999px';
            }
        }, 220);
        currentTarget = null;
    }
    
    // Afficher le popover pour un numéro
    function showPopover(numItem, slideIdx) {
        // Si déjà affiché pour ce numéro, ne rien faire
        if (currentTarget === numItem) return;
        // Annuler tout timeout précédent
        if (popoverTimeout) {
            clearTimeout(popoverTimeout);
            popoverTimeout = null;
        }
        
        // Mettre à jour le contenu
        popover.innerHTML = '';
        
        // Trouver l'URL de l'image SVG pour cette diapo
        let svgUrl = null;
        const slidesArr = Array.from(slides);
        const slide = slidesArr.find(s => parseInt(s.dataset.slideIndex ?? -1, 10) === slideIdx);
        if (slide) {
            const svgImg = slide.querySelector('img.slide-background-svg');
            svgUrl = svgImg?.src;
        }
        
        // Ajouter l'image ou le texte
        if (svgUrl) {
            const img = document.createElement('img');
            img.src = svgUrl;
            img.alt = `Preview Slide ${slideIdx + 1}`;
            img.style.display = 'block';
            img.style.maxWidth = '100%';
            img.style.maxHeight = '164px';
            img.style.borderRadius = '8px';
            img.style.background = '#fff';
            img.style.boxShadow = '0 2px 6px rgba(0,0,0,0.12)';
            popover.appendChild(img);
        } else {
            popover.textContent = `Slide ${slideIdx + 1}`;
        }
        
        // Positionner au-dessus du numéro
        const rect = numItem.getBoundingClientRect();
        popover.style.left = (rect.left + rect.width/2) + 'px';
        popover.style.top = (rect.top - 10) + 'px';
        popover.style.transform = 'translate(-50%, -100%)';
        
        // Afficher avec transition
        // Petit délai pour s'assurer que la position a été appliquée
        setTimeout(() => {
            popover.style.opacity = '1';
        }, 5);
        
        currentTarget = numItem;
    }

    slides.forEach((slide, idx) => {
        const slideIdx = parseInt(slide.dataset.slideIndex ?? idx, 10);
        const numItem = document.createElement('div');
        numItem.className = 'thumbnail-number-item';
        numItem.tabIndex = 0;
        const span = document.createElement('span');
        span.textContent = (slideIdx + 1).toString();
        span.className = 'slide-number-mini';
        numItem.appendChild(span);
        // Go to the slide on click or keyboard
        function goToSlideFromMinimalMenu() {
            let swiper = null;
            if (typeof swiperInstance !== 'undefined' && swiperInstance && typeof swiperInstance.slideTo === 'function') {
                swiper = swiperInstance;
            } else if (window.swiperInstance && typeof window.swiperInstance.slideTo === 'function') {
                swiper = window.swiperInstance;
            } else {
                // fallback: try to access the instance via .swiper.swiper
                const swiperEl = document.querySelector('.swiper');
                if (swiperEl && swiperEl.swiper && typeof swiperEl.swiper.slideTo === 'function') {
                    swiper = swiperEl.swiper;
                }
            }
            if (swiper) {
                console.log(`[MinimalNumberList] goToSlide: ${slideIdx}`);
                swiper.slideTo(slideIdx);
            } else {
                console.warn('[MinimalNumberList] Could not find a valid Swiper instance for navigation');
            }
            if (thumbnailMenuOverlay) thumbnailMenuOverlay.classList.remove('visible');
        }
        // Mouse events (anti-flicker - solution finale):
        numItem.addEventListener('mouseenter', () => {
            if (popoverTimeout) clearTimeout(popoverTimeout);
            // Delay showing popover by 500ms to avoid showing on quick movements
            popoverTimeout = setTimeout(() => showPopover(numItem, slideIdx), 500);
        });
        
        numItem.addEventListener('mouseleave', () => {
            hidePopover();
        });
        // Keyboard focus
        numItem.addEventListener('focus', () => {
            if (popoverTimeout) clearTimeout(popoverTimeout);
            popoverTimeout = setTimeout(() => showPopover(numItem, slideIdx), 500);
        });
        numItem.addEventListener('blur', hidePopover);
        // Touch: show on long press (optional, not implemented here)
        numItem.addEventListener('click', goToSlideFromMinimalMenu);
        numItem.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                goToSlideFromMinimalMenu();
            }
        });
        numberList.appendChild(numItem);
    });
}
// Generate responsive list on load
console.log('[MinimalNumberList] Registering DOMContentLoaded handler');
document.addEventListener('DOMContentLoaded', () => {
    console.log('[MinimalNumberList] DOMContentLoaded');
    generateMinimalNumberList();
});

// Debounce on resize
let minimalNumberListResizeTimeout = null;
window.addEventListener('resize', () => {
    if (minimalNumberListResizeTimeout) clearTimeout(minimalNumberListResizeTimeout);
    minimalNumberListResizeTimeout = setTimeout(() => {
        console.log('[MinimalNumberList] Window resized, regenerating list');
        generateMinimalNumberList();
    }, 120);
});

// transitionend only on opacity AND if visible
const overlayElem = document.getElementById('thumbnail-menu-overlay');
if (overlayElem) {
    overlayElem.addEventListener('transitionend', function(e) {
        if (e.propertyName === 'opacity' && this.classList.contains('visible')) {
            console.log('[MinimalNumberList] transitionend (opacity, visible), regenerating list');
            generateMinimalNumberList();
        }
    });
}
    const presentationContainer = document.getElementById("presentation-container");
    // const fullscreenButton = document.getElementById("fullscreen-button"); // removed: handled in contextual nav
    const thumbnailMenuOverlay = document.getElementById("thumbnail-menu-overlay");
    const thumbnailGrid = document.querySelector(".thumbnail-grid");
    const closeThumbnailButton = document.getElementById("close-thumbnail-menu");
    const swiperElement = document.querySelector(".swiper");
    // The laser pointer will be created dynamically
    // -------------------------------------------

    let swiperInstance = null;
    let laserPointer = null;
    let resizeTimeoutId;
    let isUpdatingPositions = false;

    // --- Critical Element Checks --- //
    if (!presentationContainer) { console.error("CRITICAL ERROR: #presentation-container not found."); alert("Error: Missing container."); return; }
    if (!thumbnailMenuOverlay || !thumbnailGrid || !closeThumbnailButton) { console.error("CRITICAL ERROR: Missing thumbnail elements."); alert("Error: Missing thumbnail elements."); return; }
    if (!swiperElement) { console.error("CRITICAL ERROR: .swiper element not found."); alert("Error: Missing swiper element."); return; }

    // --- Utility Functions --- //
    
    /**
     * Forces the reload of SVG images to ensure complete loading
     * @param {object} swiper - The Swiper instance
     * @param {boolean} includeAdjacent - Whether to also reload adjacent slides
     */
    function forceReloadSvgImages(swiper, includeAdjacent = true) {
        if (!swiper || swiper.destroyed || !swiper.slides) {
            console.warn("Cannot reload SVG images: Invalid Swiper instance");
            return;
        }
        
        const allSlides = swiper.slides || [];
        const currentIndex = swiper.activeIndex;
        const slidesToReload = [];
        
        // Get current slide and optionally adjacent slides
        if (includeAdjacent && currentIndex > 0) slidesToReload.push(allSlides[currentIndex - 1]);
        slidesToReload.push(allSlides[currentIndex]);
        if (includeAdjacent && currentIndex < allSlides.length - 1) slidesToReload.push(allSlides[currentIndex + 1]);
        
        // Reload SVG images
        slidesToReload.forEach(slide => {
            if (!slide) return;
            const svgImage = slide.querySelector('img.slide-background-svg');
            if (svgImage && svgImage.src) {
                const originalSrc = svgImage.src;
                // Force reload by adding/removing timestamp parameter
                const timestamp = new Date().getTime();
                const newSrc = originalSrc.includes('?') ? 
                    `${originalSrc}&_reload=${timestamp}` : 
                    `${originalSrc}?_reload=${timestamp}`;
                
                console.log(`Reloading SVG image for slide ${slide.dataset.slideIndex || '?'}: ${newSrc}`);
                svgImage.src = newSrc;
            }
        });
    }
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
    function handleSlideChange(swiper) { 
        if (!swiper || swiper.destroyed || !swiper.slides || swiper.slides.length === 0) { 
            console.warn("handleSlideChange: Swiper invalid/destroyed/empty."); 
            return; 
        } 
        const activeSlide = swiper.slides[swiper.activeIndex]; 
        const activeIndex = swiper.activeIndex; 
        
        if (activeSlide) { 
            requestAnimationFrame(() => updateVideoPositions(activeSlide)); 
            
            // Force reload SVG images for better display
            setTimeout(() => forceReloadSvgImages(swiper, true), 50);
        } else { 
            console.warn(`handleSlideChange: Active slide (index ${activeIndex}) not found.`); 
        } 
        
        swiper.slides.forEach((slide, index) => { 
            const videos = slide.querySelectorAll("video.slide-video-overlay"); 
            videos.forEach(videoElement => { 
                if (index === activeIndex) { 
                    if (videoElement.hasAttribute("data-autoplay")) { 
                        const playPromise = videoElement.play(); 
                        if (playPromise !== undefined) { 
                            playPromise.catch(error => { 
                                if (error.name !== 'NotAllowedError') { 
                                    console.warn(`Play failed ${videoElement.id}:`, error.message); 
                                } 
                            }); 
                        } 
                    } 
                } else { 
                    if (!videoElement.paused) { 
                        videoElement.pause(); 
                    } 
                    if (videoElement.currentTime !== 0) { 
                        videoElement.currentTime = 0; 
                    } 
                } 
            }); 
        }); 
    }
    function toggleFullScreen() { const presentationContainer = document.getElementById("presentation-container"); const notInFullscreen = (!document.fullscreenElement && !document.mozFullScreenElement && !document.webkitFullscreenElement && !document.msFullscreenElement); if (notInFullscreen) { const element = presentationContainer; if (!element) return; if (element.requestFullscreen) { element.requestFullscreen().catch(err => console.error(`FS Error: ${err.message}`)); } else if (element.mozRequestFullScreen) { element.mozRequestFullScreen(); } else if (element.webkitRequestFullscreen) { element.webkitRequestFullscreen(); } else if (element.msRequestFullscreen) { element.msRequestFullscreen(); } } else { if (document.exitFullscreen) { document.exitFullscreen().catch(err => console.error(`Exit FS Error: ${err.message}`)); } else if (document.mozCancelFullScreen) { document.mozCancelFullScreen(); } else if (document.webkitExitFullscreen) { document.webkitExitFullscreen(); } else if (document.msExitFullscreen) { document.msExitFullscreen(); } } }
    function hideThumbnailMenu() { const overlay = document.getElementById("thumbnail-menu-overlay"); if (overlay) { overlay.classList.remove('visible'); console.log("Thumbnails hidden."); } }
    function showThumbnailMenu() { if (swiperInstance && !swiperInstance.destroyed) { generateThumbnails(swiperInstance); } else { console.error("Cannot show thumbnails, swiper invalid."); if(thumbnailGrid) thumbnailGrid.innerHTML = '<p class="error-message">Error loading.</p>'; } const overlay = document.getElementById("thumbnail-menu-overlay"); if (overlay) { overlay.classList.add('visible'); console.log("Thumbnails shown."); } }
    function toggleThumbnailMenu() { const overlay = document.getElementById("thumbnail-menu-overlay"); if (overlay) { const isGoingToBeVisible = !overlay.classList.contains('visible'); if (isGoingToBeVisible) { if (swiperInstance && !swiperInstance.destroyed) { generateThumbnails(swiperInstance); } else { console.error("Cannot show/gen thumbs, swiper invalid."); if(thumbnailGrid) thumbnailGrid.innerHTML = '<p class="error-message">Error loading.</p>'; } } overlay.classList.toggle('visible'); console.log(`Thumbnails ${overlay.classList.contains('visible')?'shown':'hidden'}.`); } }
    function generateThumbnails(swiper) { if (!swiper || swiper.destroyed || !swiper.slides || !thumbnailGrid) { console.error("Cannot generate thumbnails: Swiper invalid or grid missing."); if (thumbnailGrid) thumbnailGrid.innerHTML = '<p class="error-message">Error loading.</p>'; return; } console.log("Generating thumbnails..."); thumbnailGrid.innerHTML = ''; swiper.slides.forEach((slide, index) => { const slideIndex = parseInt(slide.dataset.slideIndex ?? index, 10); const svgImgElement = slide.querySelector('img.slide-background-svg'); const svgUrl = svgImgElement?.src; const thumbItem = document.createElement('div'); thumbItem.classList.add('thumbnail-item'); thumbItem.dataset.gotoSlide = slideIndex; if (svgUrl) { const img = document.createElement('img'); img.src = svgUrl; img.alt = `Thumb ${slideIndex + 1}`; img.loading = 'lazy'; thumbItem.appendChild(img); } else { const fallback = document.createElement('span'); fallback.textContent = `Slide ${slideIndex + 1}`; fallback.style.cssText='font-size:0.8em;color:#666;'; thumbItem.appendChild(fallback); } const numSpan = document.createElement('span'); numSpan.classList.add('slide-number'); numSpan.textContent = slideIndex + 1; thumbItem.appendChild(numSpan); thumbItem.addEventListener('click', () => { const targetIndex = parseInt(thumbItem.dataset.gotoSlide, 10); if (!isNaN(targetIndex) && swiper && !swiper.destroyed) { console.log(`Thumb -> Slide ${targetIndex}`); swiper.slideTo(targetIndex); hideThumbnailMenu(); } }); thumbnailGrid.appendChild(thumbItem); }); const count = swiper.slides?.length ?? 0; console.log(`${count} thumbnails generated.`); }

    /** Creates a new laser pointer */
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
            mix-blend-mode: normal;
            visibility: visible !important;
            opacity: 1 !important;
        `;
        return laser;
    }

    /** Updates the visibility of the laser pointer */
    function updateLaserPointerVisibility() {
        const fullscreenElement = (
            document.fullscreenElement || document.webkitFullscreenElement ||
            document.mozFullScreenElement || document.msFullscreenElement
        );

        console.log(`DEBUG: Fullscreen change detected, element:`, fullscreenElement);

        // Remove the old pointer if it exists
        if (laserPointer && laserPointer.parentNode) {
            laserPointer.parentNode.removeChild(laserPointer);
            laserPointer = null;
        }

        if (fullscreenElement) {
            // Create a new pointer
            laserPointer = createLaserPointer();
            // Add it directly to the fullscreen element
            fullscreenElement.appendChild(laserPointer);
            console.log('DEBUG: New laser pointer created and attached');
        }
    }

    /** Handles mouse movement for the laser pointer */
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
        // No need for the isFullscreen log here, updateLaserPointerVisibility does it already
        console.log("DEBUG: handleFullscreenChange event triggered.");

        // Update pointer visibility
        updateLaserPointerVisibility();

        // Force reload SVG images to ensure complete loading in any mode
        const fullscreenElement = (
            document.fullscreenElement || document.webkitFullscreenElement ||
            document.mozFullScreenElement || document.msFullscreenElement
        );
        
        console.log(fullscreenElement ? "DEBUG: Fullscreen detected" : "DEBUG: Standard mode detected");
        console.log("Reloading SVG images...");
        
        // Reload SVG images always - not just in fullscreen
        setTimeout(() => {
            if (swiperInstance && !swiperInstance.destroyed) {
                forceReloadSvgImages(swiperInstance, true);
            }
        }, 100); // Short delay before reloading images

        // Update Swiper after a delay
        setTimeout(() => {
            if (swiperInstance && !swiperInstance.destroyed) {
                swiperInstance.update();
                console.log("Swiper updated after fullscreen change timeout.");
                const currentSlide = swiperInstance.slides?.[swiperInstance.activeIndex];
                if (currentSlide) {
                    requestAnimationFrame(() => {
                        updateVideoPositions(currentSlide);
                    });
                }
            } else {
                console.warn("handleFullscreenChange timeout: Swiper instance invalid/destroyed.");
            }
        }, 300); // Keep the delay for Swiper/video update
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
                        if (!swiperInstance || swiperInstance.destroyed || !swiperInstance.slides || swiperInstance.slides.length === 0) { 
                            console.warn("Resize timeout: Swiper invalid/empty."); 
                            return; 
                        }
                        const currentSlide = swiperInstance.slides[swiperInstance.activeIndex];
                        if (currentSlide) { 
                            updateVideoPositions(currentSlide); 
                            // Force reload SVG images after resize
                            forceReloadSvgImages(swiperInstance, true);
                        }
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
    // (fullscreen button binding moved into contextual navigation logic)

    // --- Laser Pointer Functions ---
    // Listeners for fullscreen (call the modified handleFullscreenChange function)
    console.log("Adding fullscreen change listeners...");
    // --- Event Listeners ---
    window.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('fullscreenchange', updateLaserPointerVisibility);
    document.addEventListener('webkitfullscreenchange', updateLaserPointerVisibility);
    document.addEventListener('mozfullscreenchange', updateLaserPointerVisibility);
    document.addEventListener('MSFullscreenChange', updateLaserPointerVisibility);

    // Update fullscreen button icon on change
    function updateFullscreenIcon() {
        const btn = document.getElementById('fullscreen-button');
        const fsElem = document.fullscreenElement || document.webkitFullscreenElement || document.mozFullScreenElement || document.msFullscreenElement;
        if (btn) {
            if (fsElem) btn.classList.add('fs'); else btn.classList.remove('fs');
        }
    }
    ['fullscreenchange','webkitfullscreenchange','mozfullscreenchange','MSFullscreenChange'].forEach(evt => document.addEventListener(evt, updateFullscreenIcon));
    updateFullscreenIcon();

    // Add listeners for videos
    document.querySelectorAll('video').forEach(video => {
        video.addEventListener('dblclick', () => {
            // Create the pointer before going fullscreen
            if (laserPointer && laserPointer.parentNode) {
                laserPointer.parentNode.removeChild(laserPointer);
            }
            laserPointer = createLaserPointer();
            document.body.appendChild(laserPointer);
            
            // Go fullscreen
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

    // Add event listeners to existing videos
    document.querySelectorAll('video').forEach(video => {
        video.addEventListener('fullscreenchange', handleFullscreenChange);
        video.addEventListener('webkitfullscreenchange', handleFullscreenChange);
        video.addEventListener('mozfullscreenchange', handleFullscreenChange);
        video.addEventListener('MSFullscreenChange', handleFullscreenChange);
    });

    // Observe new videos added dynamically
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

    // Observe changes in the entire document
    videoObserver.observe(document.body, {
        childList: true,
        subtree: true
    });

    // Add listener for mouse movement
    console.log("Adding mousemove listener...");
    document.addEventListener("mousemove", handleMouseMove);

    // --- Contextual navigation buttons --- //
    (function() {
        const container = document.querySelector('.swiper-container-wrapper');
        if (!container) return;
        const edgeZone = 48;
        let hideTimeout = null, lastEdge = null;
        function showNav() {
            container.classList.add('context-nav-visible');
            if (hideTimeout) { clearTimeout(hideTimeout); hideTimeout = null; }
        }
        function scheduleHideNav() {
            if (hideTimeout) clearTimeout(hideTimeout);
            hideTimeout = setTimeout(() => {
                container.classList.remove('context-nav-visible');
                lastEdge = null;
            }, 500);
        }
        function handleMouseMove(e) {
            const rect = container.getBoundingClientRect();
            const x = e.clientX - rect.left, y = e.clientY - rect.top;
            if (x<0||y<0||x>rect.width||y>rect.height) return;
            let edge = null;
            if (x <= edgeZone) edge = 'left';
            else if (x >= rect.width - edgeZone) edge = 'right';
            else if (y <= edgeZone && x >= rect.width - 2*edgeZone) edge = 'topright';
            if (edge) { lastEdge = edge; showNav(); }
        }
        container.addEventListener('mousemove', handleMouseMove, {passive:true});
        container.querySelectorAll('.context-nav-btn').forEach(btn => {
            btn.addEventListener('focus', showNav);
            btn.addEventListener('mouseenter', showNav);
            btn.addEventListener('mouseleave', scheduleHideNav);
        });
        container.querySelector('#nav-prev')?.addEventListener('click', () => { swiperInstance.slidePrev(); showNav(); });
        container.querySelector('#nav-next')?.addEventListener('click', () => { swiperInstance.slideNext(); showNav(); });
        container.querySelector('#nav-menu')?.addEventListener('click', () => { toggleThumbnailMenu(); showNav(); });
        container.querySelector('#fullscreen-button')?.addEventListener('click', () => { toggleFullScreen(); showNav(); });
        container.addEventListener('click', e => {
            // Slide navigation on click outside nav buttons
            const el = e.target instanceof Element ? e.target : e.target.parentElement;
            if (!el || !el.closest('.context-nav-btn')) {
                swiperInstance.slideNext();
                showNav();
            }
        });
        // Hide nav when leaving container area
        container.addEventListener('mouseleave', scheduleHideNav);
    })();

    // Keyboard listener
    document.addEventListener('keydown', (event) => {
        if (!swiperInstance || swiperInstance.destroyed || !swiperInstance.enabled) { return; }
        // évite l’erreur si event.target n’est pas un element
        const targetTagName = (event.target && event.target.tagName) ? event.target.tagName.toLowerCase() : '';
        if (['input','textarea','select'].includes(targetTagName)) { return; }
        const isMenuVisible = thumbnailMenuOverlay?.classList.contains('visible');
        const isMenuKey = ['Escape','m','M'].includes(event.key);
        if (isMenuVisible && !isMenuKey) { return; }
        let shouldPreventDefault = true;
        switch (event.key) {
            case 'ArrowRight': case 'PageDown': case ' ': if (!event.shiftKey) { swiperInstance.slideNext(); } else { shouldPreventDefault = false; } break;
            case 'ArrowLeft': case 'PageUp': swiperInstance.slidePrev(); break;
            case 'Home': swiperInstance.slideTo(0); break;
            case 'End': if (swiperInstance.slides?.length > 0) { swiperInstance.slideTo(swiperInstance.slides.length - 1); } break;
            case 'f': case 'F': toggleFullScreen(); break;
            case 'm': case 'M': toggleThumbnailMenu(); break;
            case 'Escape': if (isMenuVisible) { hideThumbnailMenu(); } else { shouldPreventDefault = false; } break;
            default: shouldPreventDefault = false; break;
        }
        if (shouldPreventDefault) { event.preventDefault(); }
    });

    // Thumbnail menu listeners
    if (thumbnailMenuOverlay) { thumbnailMenuOverlay.addEventListener('click', (event) => { if (event.target === thumbnailMenuOverlay) { hideThumbnailMenu(); } }); }
    if (closeThumbnailButton) { closeThumbnailButton.addEventListener('click', hideThumbnailMenu); }

    // Window load listener
    window.addEventListener("load", () => { console.log("Window 'load' event received."); setTimeout(() => { if (!swiperInstance || swiperInstance.destroyed || !swiperInstance.slides || swiperInstance.slides.length === 0) { console.warn("Window load timeout: Swiper invalid/empty."); return; } const currentSlide = swiperInstance.slides[swiperInstance.activeIndex]; if (currentSlide) { updateVideoPositions(currentSlide); } else { console.warn("Window load timeout: Active slide not found."); } }, 300); });

    // --- LASER POINTER FUNCTIONS ---
    // Initial check for laser pointer visibility
    if(laserPointer) {
        console.log("Performing initial laser pointer visibility check...");
        updateLaserPointerVisibility(); // Set initial state (should be hidden)
    }
    // --- END LASER POINTER FUNCTIONS ---

}); // End DOMContentLoaded listener
