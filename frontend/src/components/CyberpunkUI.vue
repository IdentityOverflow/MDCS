<template>
  <div class="container">
    <div class="inner-content-wrapper">
      <!-- Extended grid background -->
      <div class="extended-grid"></div>

      <!-- Circular layers from innermost to outermost -->
      <div class="ring ring-1"></div>
      <div class="ring ring-2"></div>
      <div class="ring ring-3"></div>
      <div class="ring ring-4"></div>
      <div class="ring ring-5"></div>
      <div class="ring ring-6"></div>

      <!-- Tech detail arcs -->
      <div class="tech-details">
        <div class="arc arc-1"></div>
        <div class="arc arc-2"></div>
      </div>

      <!-- Main rectangular screen -->
      <div class="screen">
        <div class="screen-inner">
          <div class="scan-line"></div>
          <div class="screen-content">{{ mainScreenText }}</div>
          <div class="bracket bracket-tl"></div>
          <div class="bracket bracket-tr"></div>
          <div class="bracket bracket-bl"></div>
          <div class="bracket bracket-br"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

const mainScreenText = ref('SYSTEM LIVE')

const mainMessages = ['SYSTEM LIVE', 'SCANNING', 'AUTHENTICATED', 'PROCESSING', 'ANALYZING']

let mainIndex = 0

onMounted(() => {
  setInterval(() => {
    mainIndex = (mainIndex + 1) % mainMessages.length
    mainScreenText.value = mainMessages[mainIndex]
  }, 3000)
})
</script>

<style scoped>
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

/* When activated, has interesting effect */
/* .container {
    position: relative;
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
} */

.inner-content-wrapper {
    position: relative;
    width: 700px; /* Original width of the full UI */
    height: 700px; /* Original height of the full UI */
    display: flex;
    align-items: center;
    justify-content: center;
    transform: scale(0.25); /* Scale down the entire content */
    transform-origin: center center;
}

/* Extended grid overlay that goes beyond screen */
.extended-grid {
    position: absolute;
    width: 600px;
    height: 600px;
    background-image: 
        repeating-linear-gradient(0deg, transparent, transparent 15px, rgba(0, 255, 65, 0.03) 15px, rgba(0, 255, 65, 0.03) 16px),
        repeating-linear-gradient(90deg, transparent, transparent 15px, rgba(0, 255, 65, 0.03) 15px, rgba(0, 255, 65, 0.03) 16px);
    pointer-events: none;
    z-index: 1;
}

/* Main rectangular screen - now larger */
.screen {
    position: absolute;
    width: 480px;
    height: 320px;
    z-index: 10;
    /* Clip bottom corners */
    clip-path: polygon(
        0 0,
        100% 0,
        100% calc(100% - 40px),
        calc(100% - 60px) calc(100% - 40px),
        calc(100% - 60px) 100%,
        60px 100%,
        60px calc(100% - 40px),
        0 calc(100% - 40px)
    );
}

/* Inner content container */
.screen-inner {
    position: absolute;
    width: 100%;
    height: 100%;
    background: linear-gradient(135deg, #0a1628 0%, #1e3a5f 50%, #0a1628 100%);
    border: 2px solid #00ff41;
    overflow: hidden;
    box-shadow: 
        0 0 50px rgba(0, 255, 65, 0.5),
        inset 0 0 30px rgba(0, 255, 65, 0.1);
    clip-path: inherit;
}

.screen-content {
    position: absolute;
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 28px;
    font-weight: bold;
    letter-spacing: 4px;
    text-transform: uppercase;
    color: #00ff41;
    text-shadow: 0 0 10px rgba(0, 255, 65, 0.8);
    animation: flicker 2s infinite;
    z-index: 2;
}

.scan-line {
    position: absolute;
    width: 100%;
    height: 2px;
    background: linear-gradient(90deg, transparent, #00ff41, transparent);
    animation: scan 3s linear infinite;
    z-index: 3;
}

@keyframes scan {
    0% { top: 0%; }
    100% { top: 100%; }
}

/* Circular layers */
.ring {
    position: absolute;
    border-radius: 50%;
    pointer-events: none;
}

/* First inner ring - BLUE and THICKER */
.ring-1 {
    width: 380px;
    height: 380px;
    border: 4px solid #0088ff;
    opacity: 0.9;
    animation: rotate 10s linear infinite;
    box-shadow: 0 0 20px rgba(0, 136, 255, 0.6);
}

.ring-1::before {
    content: '';
    position: absolute;
    width: 100%;
    height: 100%;
    border-radius: 50%;
    border: 2px solid #0088ff;
    border-style: dashed;
    animation: rotate-reverse 15s linear infinite;
    opacity: 0.6;
}

/* Second ring - BLUE and THICKER */
.ring-2 {
    width: 440px;
    height: 440px;
    border: 3px solid #0088ff;
    background: conic-gradient(
        from 0deg,
        transparent 0deg,
        rgba(0, 136, 255, 0.3) 10deg,
        transparent 20deg,
        transparent 40deg,
        rgba(0, 136, 255, 0.3) 50deg,
        transparent 60deg,
        transparent 100deg,
        rgba(0, 136, 255, 0.3) 110deg,
        transparent 120deg,
        transparent 180deg,
        rgba(0, 136, 255, 0.3) 190deg,
        transparent 200deg,
        transparent 270deg,
        rgba(0, 136, 255, 0.3) 280deg,
        transparent 290deg,
        transparent 350deg,
        rgba(0, 136, 255, 0.3) 360deg
    );
    animation: rotate 20s linear infinite;
    box-shadow: 0 0 15px rgba(0, 136, 255, 0.4);
}

/* Third ring - BLUE and THICKER */
.ring-3 {
    width: 500px;
    height: 500px;
    border: 3px solid #0088ff;
    background: repeating-conic-gradient(
        from 0deg at 50% 50%,
        transparent 0deg,
        transparent 2deg,
        rgba(0, 136, 255, 0.2) 2deg,
        rgba(0, 136, 255, 0.2) 3deg
    );
    animation: rotate-reverse 25s linear infinite;
    opacity: 0.7;
    box-shadow: 0 0 10px rgba(0, 136, 255, 0.3);
}

/* Fourth ring - INVERTED: varying segment sizes with fewer gaps */
.ring-4 {
    width: 560px;
    height: 560px;
    background: conic-gradient(
        from 0deg,
        transparent 0deg 4deg,
        #00ff41 4deg 75deg,
        transparent 75deg 78deg,
        #00ff41 78deg 120deg,
        transparent 120deg 124deg,
        #00ff41 124deg 210deg,
        transparent 210deg 213deg,
        #00ff41 213deg 245deg,
        transparent 245deg 249deg,
        #00ff41 249deg 340deg,
        transparent 340deg 344deg,
        #00ff41 344deg 360deg
    );
    -webkit-mask: radial-gradient(
        transparent 270px,
        black 270px,
        black 280px,
        transparent 280px
    );
    mask: radial-gradient(
        transparent 270px,
        black 270px,
        black 280px,
        transparent 280px
    );
    animation: rotate 30s linear infinite;
    opacity: 0.8;
}

/* Outer ring with tick marks - BLUE and THICKER */
.ring-5 {
    width: 620px;
    height: 620px;
    background: repeating-conic-gradient(
        from 0deg at 50% 50%,
        #0088ff 0deg 0.5deg,
        transparent 0.5deg 6deg
    );
    -webkit-mask: radial-gradient(
        transparent 295px,
        black 295px,
        black 315px,
        transparent 315px
    );
    mask: radial-gradient(
        transparent 295px,
        black 295px,
        black 315px,
        transparent 315px
    );
    opacity: 0.8;
    animation: rotate-reverse 40s linear infinite;
}

/* Outermost decorative ring - BLUE and THICKER */
.ring-6 {
    width: 680px;
    height: 680px;
    border: 3px solid #0088ff;
    opacity: 0.5;
    box-shadow: 
        0 0 30px rgba(0, 136, 255, 0.3),
        inset 0 0 30px rgba(0, 136, 255, 0.1);
}

/* Tech details overlay */
.tech-details {
    position: absolute;
    width: 100%;
    height: 100%;
    pointer-events: none;
}

.arc {
    position: absolute;
    width: 100%;
    height: 100%;
    border-radius: 50%;
    border: 2px solid transparent;
}

.arc-1 {
    border-top-color: #0088ff;
    border-right-color: #0088ff;
    border-width: 10px;
    animation: rotate 8s linear infinite;
}

.arc-2 {
    width: 90%;
    height: 90%;
    top: 5%;
    left: 5%;
    border-bottom-color: #0088ff;
    border-left-color: #0088ff;
    border-width: 10px;
    animation: rotate-reverse 12s linear infinite;
}

/* Corner brackets */
.bracket {
    position: absolute;
    width: 60px;
    height: 40px;
    border: 1px solid #00ff41;
    z-index: 12;
}

.bracket-tl {
    top: -2px;
    left: -2px;
    border-right: none;
    border-bottom: none;
}

.bracket-tr {
    top: -2px;
    right: -2px;
    border-left: none;
    border-bottom: none;
}

.bracket-bl {
    bottom: 0;
    left: 0;
    border-left: none;
    border-bottom: none;
}

.bracket-br {
    bottom: 0;
    right: 0px;
    border-right: none;
    border-bottom: none;
}


@keyframes rotate {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

@keyframes rotate-reverse {
    from { transform: rotate(360deg); }
    to { transform: rotate(0deg); }
}

@keyframes pulse-dot {
    0%, 100% { opacity: 0.3; transform: scale(1); }
    50% { opacity: 1; transform: scale(1.5); }
}

@keyframes flicker {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.85; }
}

/* Glitch effect on hover */
.container:hover .screen-content {
    animation: glitch 0.3s infinite;
}

@keyframes glitch {
    0%, 100% { 
        text-shadow: 
            0 0 10px rgba(0, 255, 65, 0.8),
            2px 2px 2px rgba(255, 0, 0, 0.5);
    }
    25% { 
        text-shadow: 
            0 0 10px rgba(0, 255, 65, 0.8),
            -2px -2px 2px rgba(0, 136, 255, 0.5);
    }
    50% { 
        text-shadow: 
            0 0 10px rgba(0, 255, 65, 0.8),
            2px -2px 2px rgba(138, 43, 226, 0.5);
    }
}
</style>