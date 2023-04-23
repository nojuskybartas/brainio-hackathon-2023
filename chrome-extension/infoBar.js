const checkEndpoint = async() => {
    const dev = document.getElementById("lazarus-connect-device")
    const status = document.getElementById("lazarus-connect-status")

    try {
        await fetch("http://127.0.0.1:96/device")
        status.innerText = "Connected"
        dev.innerHTML = "Unicorn"
    } catch {
        status.innerText = "Not Connected"  
        dev.innerHTML = "None"
        clearInterval(interval)
    }
    
}
let interval = setInterval(checkEndpoint, 1000)

let html = `
    <style> .infoBar {
        display: none;
    }
    </style>
    <h5 id="lazarus-connect-status">Connecting...</h5>
    
    <h5>Device: <snap id="lazarus-connect-device"></span></h5>
`

if (!document.getElementById("#lazarus-infoBar")) {
    const el = document.createElement("div")
    el.id = "lazarus-infoBar"
    el.innerHTML = html
    el.className = "infoBar"
    const h = document.getElementsByTagName("html")[0]
    h.appendChild(el)
}

