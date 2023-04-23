chrome.runtime.onInstalled.addListener(() => {
  chrome.action.setBadgeText({
    text: "OFF",
  });
});

const extensions = "https://developer.chrome.com/docs/extensions";
const kucoin = "https://www.kucoin.com";

let tabData: any = {};

let timeout: any
let tradingBlocked = false
let prevTradingBlocked = false

// When the user clicks on the extension action
chrome.action.onClicked.addListener(async (tab) => {
  if (tab?.url?.startsWith(extensions) || tab?.url?.startsWith(kucoin)) {
    // We retrieve the action badge to check if the extension is 'ON' or 'OFF'
    const prevState = await chrome.action.getBadgeText({ tabId: tab.id });
    // Next state will always be the opposite
    const nextState = prevState === "ON" ? "OFF" : "ON";

    await chrome.scripting.executeScript({
      target: { tabId: tab.id! },
      files: ["infoBar.js"]
    })

    // Set the action badge to the next state
    await chrome.action.setBadgeText({
      tabId: tab.id,
      text: nextState,
    });

    const resetChanges = async() => {
      // clearInterval(timeout)

      await chrome.scripting.removeCSS({
        files: ["focus-mode.css"],
        target: { tabId: tab.id! },
      });

      chrome.scripting.executeScript({
        target: { tabId: tab.id! },
        func: () => {
          const popupContainer = document.getElementById(
            "popup-container-lazarus"
          );
          popupContainer?.remove();
        },
      });
    }

    const checkIsTradingBlocked = async() => {
      try {
        const res = await fetch("http://127.0.0.1:96/blockTrading")
        
        // if (!res.ok) {
        //     tradingBlocked = false
            // clearInterval(timeout)
            // if (el) el.innerText = "Connected"
            
        // } else {
            // if (!timeout) timeout = setInterval(checkIsTradingBlocked, 2000)
            // if (el) el.innerText = "Not Connected" 
        // }

        try {
          tradingBlocked = await res.text() === "True" ? true : false
        } catch (e) {
          console.warn(e)
        }

        if (tradingBlocked === prevTradingBlocked) return
        prevTradingBlocked = tradingBlocked

        if (tradingBlocked) {

          await chrome.scripting.insertCSS({
            files: ["focus-mode.css"],
            target: { tabId: tab.id! },
          });
    
          chrome.scripting.executeScript({
            target: { tabId: tab.id! },
            args: [
              {
                heroImgSrc: chrome.runtime.getURL("bomb.png"),
                bgImgSrc: chrome.runtime.getURL("background.jpg"),
                htmlSrc: chrome.runtime.getURL("popup.html"),
                audioSrc: chrome.runtime.getURL("soothing-audio-1.mp3"),
              },
            ],
            func: (args) => {
              fetch(args.htmlSrc)
                .then((resp) => resp.text())
                .then((html) => {
                  const popupContainer = document.createElement("div");
                  popupContainer.innerHTML = html;
                  popupContainer.id = "popup-container-lazarus";
                  const styleContainer = document.createElement("style");
                  styleContainer.innerHTML = `
                    .bg_image {
                      background-image: url(${args.bgImgSrc});
                    }
                  `;
                  popupContainer.appendChild(styleContainer);
    
                  const heroImg = popupContainer.querySelector("img");
                  heroImg!.src = args.heroImgSrc;
    
                  const audio = document.createElement("audio");
                  popupContainer.appendChild(audio);
    
                  audio!.src = args.audioSrc;
                  audio!.volume = 1;
                  audio!.loop = true;
                  audio!.autoplay = true;
    
                  document.body.appendChild(popupContainer);
                });
            },
          });
        } else {
          await resetChanges()
        } 
      } catch (e) {
        console.warn(e)
      }
    }

    if (nextState === "ON") {

      timeout = setInterval(checkIsTradingBlocked, 3000)

      await chrome.scripting.insertCSS({
        files: ["infoBar.css"],
        target: { tabId: tab.id! },
      });

      
    } else {

      await chrome.scripting.removeCSS({
        files: ["infoBar.css"],
        target: { tabId: tab.id! },
      });

      await resetChanges();
    }
  
    
  } 
});