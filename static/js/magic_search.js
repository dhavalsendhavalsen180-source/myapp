~/.../static/js $ cat magic_search.js
/* ==========================================
   MAGIC SEARCH JS
   Part 1 — Init + Floating Particles
========================================== */

document.addEventListener("DOMContentLoaded",()=>{

const wrap=document.querySelector(".magic-search-wrap");

if(!wrap) return;

/* Layers */

const particleLayer=document.createElement("div");
particleLayer.className="particle-layer";

const electricLayer=document.createElement("div");
electricLayer.className="electric-flow";

const lightningLayer=document.createElement("div");
lightningLayer.className="lightning-layer";

const burstLayer=document.createElement("div");
burstLayer.className="burst-layer";

wrap.appendChild(particleLayer);
wrap.appendChild(electricLayer);
wrap.appendChild(lightningLayer);
wrap.appendChild(burstLayer);

/* ==========================
   FLOATING PARTICLES
========================== */

function createParticle(){

    const p=document.createElement("span");

    p.className="magic-particle";

    p.style.left=Math.random()*100+"%";

    p.style.top=Math.random()*100+"%";

    const size=2+Math.random()*5;

    p.style.width=size+"px";
    p.style.height=size+"px";

    p.style.animationDuration=
        (3+Math.random()*6)+"s";

    p.style.animationDelay=
        (Math.random()*4)+"s";

    p.style.opacity=.3+Math.random()*.7;

    const colors=[
        "#00ffff",
        "#00ff99",
        "#ffd700",
        "#ff66ff",
        "#ffffff",
        "#66ccff"
    ];

    p.style.background=
        colors[Math.floor(Math.random()*colors.length)];

    p.style.boxShadow=
        "0 0 10px "+p.style.background;

    particleLayer.appendChild(p);

}

/* Create 100 particles */

for(let i=0;i<100;i++){

    createParticle();

}

});
/* ==========================================
   PART 2 — ELECTRIC CURRENT ENGINE
========================================== */

const electricColors=[
    "#00ffff",
    "#00bfff",
    "#ffffff",
    "#ffe600",
    "#7df9ff"
];

function createElectricLine(){

    const line=document.createElement("div");

    line.className="electric-line";

    line.style.top=(8+Math.random()*40)+"px";

    line.style.left="-180px";

    line.style.width=(80+Math.random()*120)+"px";

    line.style.animationDuration=
        (.6+Math.random()*.8)+"s";

    line.style.background=
        "linear-gradient(90deg,transparent,"
        +electricColors[Math.floor(Math.random()*electricColors.length)]
        +",#ffffff,"
        +electricColors[Math.floor(Math.random()*electricColors.length)]
        +",transparent)";

    electricLayer.appendChild(line);

    /* Random Branch */

    if(Math.random()>.55){

        const branch=document.createElement("div");

        branch.className="electric-line";

        branch.style.top=
            (parseFloat(line.style.top)+
            (-8+Math.random()*16))+"px";

        branch.style.left="-180px";

        branch.style.width=
            (40+Math.random()*80)+"px";

        branch.style.transform=
            "rotate("+
            (-20+Math.random()*40)
            +"deg)";

        branch.style.animationDuration=
            (.5+Math.random()*.6)+"s";

        branch.style.opacity=".75";

        electricLayer.appendChild(branch);

        setTimeout(()=>{
            branch.remove();
        },1800);

    }

    setTimeout(()=>{
        line.remove();
    },1800);

}

/* Continuous Current */

setInterval(()=>{

    createElectricLine();

},140);
/* ==========================================
   PART 3 — LIGHTNING ENGINE
========================================== */

function createLightning(){

    const bolt=document.createElement("div");

    bolt.className="lightning";

    bolt.style.left=
        (10+Math.random()*85)+"%";

    bolt.style.top=
        (-5+Math.random()*8)+"px";

    bolt.style.height=
        (45+Math.random()*45)+"px";

    bolt.style.transform=
        "rotate("+
        (-35+Math.random()*70)+
        "deg)";

    bolt.style.opacity=.8;

    lightningLayer.appendChild(bolt);

    /* Screen Flash */

    wrap.animate([

        {
            filter:"brightness(1)"
        },

        {
            filter:"brightness(1.25)"
        },

        {
            filter:"brightness(1)"
        }

    ],{

        duration:180,

        easing:"ease-out"

    });

    setTimeout(()=>{

        bolt.remove();

    },350);

}

/* Random Lightning */

function lightningLoop(){

    const delay=
        1500+
        Math.random()*3500;

    setTimeout(()=>{

        if(Math.random()>.35){

            createLightning();

        }

        lightningLoop();

    },delay);

}

lightningLoop();
/* ==========================================
   PART 4 — FLOATING MAGIC PARTICLES
========================================== */

const particleColors=[
    "#00ffff",
    "#00ff99",
    "#66ccff",
    "#ffd700",
    "#ff66ff",
    "#ffffff",
    "#8a2be2"
];

function createParticle(){

    const p=document.createElement("span");

    p.className="magic-particle";

    const size=2+Math.random()*6;

    p.style.width=size+"px";
    p.style.height=size+"px";

    p.style.left=(Math.random()*100)+"%";
    p.style.top=(Math.random()*100)+"%";

    const color=
        particleColors[
            Math.floor(
                Math.random()*particleColors.length
            )
        ];

    p.style.background=color;

    p.style.boxShadow=
        "0 0 8px "+color+
        ",0 0 16px "+color;

    particleLayer.appendChild(p);

    let x=(Math.random()-.5)*40;
    let y=(Math.random()-.5)*40;

    const life=3000+Math.random()*4000;

    p.animate([

        {
            transform:
                "translate(0px,0px) scale(.3)",
            opacity:0
        },

        {
            transform:
                "translate("+x+"px,"+y+"px) scale(1)",
            opacity:1,
            offset:.2
        },

        {
            transform:
                "translate("+(x*2)+"px,"+(y-60)+"px) scale(.2)",
            opacity:0
        }

    ],{

        duration:life,
        easing:"linear"

    });

    setTimeout(()=>{

        p.remove();

    },life);

}

/* Create 150 particles */

for(let i=0;i<150;i++){

    setTimeout(createParticle,i*35);

}

/* Infinite Generator */

setInterval(()=>{

    createParticle();

},70);
/* ==========================================
   PART 5 — TOUCH / FINGER ENERGY BURST
========================================== */

function createBurst(x,y){

    for(let i=0;i<24;i++){

        const spark=document.createElement("span");

        spark.className="energy-spark";

        spark.style.left=x+"px";
        spark.style.top=y+"px";

        const angle=(Math.PI*2/24)*i;
        const distance=30+Math.random()*45;

        const dx=Math.cos(angle)*distance;
        const dy=Math.sin(angle)*distance;

        const colors=[
            "#00ffff",
            "#00ff88",
            "#ffd700",
            "#ffffff",
            "#ff66ff"
        ];

        const color=
            colors[Math.floor(Math.random()*colors.length)];

        spark.style.background=color;
        spark.style.boxShadow=
            "0 0 8px "+color+
            ",0 0 18px "+color;

        burstLayer.appendChild(spark);

        spark.animate([
            {
                transform:"translate(0,0) scale(.4)",
                opacity:1
            },
            {
                transform:`translate(${dx}px,${dy}px) scale(1.3)`,
                opacity:.9,
                offset:.6
            },
            {
                transform:`translate(${dx*1.4}px,${dy*1.4}px) scale(.2)`,
                opacity:0
            }
        ],{
            duration:700,
            easing:"ease-out"
        });

        setTimeout(()=>{
            spark.remove();
        },700);

    }

}

/* Mouse */

wrap.addEventListener("mousemove",(e)=>{

    if(Math.random()>.82){

        const r=wrap.getBoundingClientRect();

        createBurst(
            e.clientX-r.left,
            e.clientY-r.top
        );

    }

});

/* Touch */

wrap.addEventListener("touchstart",(e)=>{

    const r=wrap.getBoundingClientRect();

    const t=e.touches[0];

    createBurst(
        t.clientX-r.left,
        t.clientY-r.top
    );

});

/* Focus Burst */

const input=wrap.querySelector(".magic-search");

if(input){

    input.addEventListener("focus",()=>{

        const r=wrap.getBoundingClientRect();

        createBurst(
            r.width/2,
            r.height/2
        );

    });

}
/* ==========================================
   PART 6 — 3D PARALLAX ENGINE
========================================== */

const input = wrap.querySelector(".magic-search");

function updateParallax(x, y){

    const rect = wrap.getBoundingClientRect();

    const px = ((x - rect.left) / rect.width - 0.5) * 2;
    const py = ((y - rect.top) / rect.height - 0.5) * 2;

    wrap.style.transform =
        `perspective(900px)
         rotateY(${px * 8}deg)
         rotateX(${-py * 8}deg)
         scale(1.02)`;

    if(input){

        input.style.transform =
            `translateZ(18px)
             translate(${px * 4}px, ${py * 4}px)`;

    }

}

function resetParallax(){

    wrap.style.transform =
        "perspective(900px) rotateX(0deg) rotateY(0deg) scale(1)";

    if(input){

        input.style.transform =
            "translateZ(0px) translate(0px,0px)";

    }

}

/* Mouse */

wrap.addEventListener("mousemove",(e)=>{

    updateParallax(e.clientX,e.clientY);

});

/* Touch */

wrap.addEventListener("touchmove",(e)=>{

    const t=e.touches[0];

    updateParallax(t.clientX,t.clientY);

},{passive:true});

/* Leave */

wrap.addEventListener("mouseleave",resetParallax);

wrap.addEventListener("touchend",resetParallax);

/* Auto Floating */

let floatAngle = 0;

setInterval(()=>{

    floatAngle += 0.05;

    const y = Math.sin(floatAngle) * 2;

    wrap.style.translate = `0 ${y}px`;

},30);
