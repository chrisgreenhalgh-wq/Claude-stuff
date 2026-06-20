// micro:bit Watch Program
// Displays time of day (hours, minutes, seconds)
// Time text appears in red on a black (off) background - the only colour the micro:bit LEDs support

let hours = 0
let minutes = 0
let seconds = 0
let settingMode = true
let settingField = 0   // 0 = hours, 1 = minutes, 2 = seconds
let lastTickTime = 0

// Returns a 2-digit string, e.g. 9 becomes "09"
function pad(n: number): string {
    if (n < 10) {
        return "0" + n
    }
    return "" + n
}

function showCurrentTime() {
    basic.showString(pad(hours) + ":" + pad(minutes) + ":" + pad(seconds))
}

// --- BUTTON A ---
// Setting mode: increment the current field
// Running mode: show current time
input.onButtonPressed(Button.A, function () {
    if (settingMode) {
        if (settingField == 0) {
            hours = (hours + 1) % 24
            basic.showNumber(hours)
        } else if (settingField == 1) {
            minutes = (minutes + 1) % 60
            basic.showNumber(minutes)
        } else {
            seconds = (seconds + 1) % 60
            basic.showNumber(seconds)
        }
    } else {
        showCurrentTime()
    }
})

// --- BUTTON B ---
// Setting mode: confirm current field and move to the next one
//   After the last field, start the clock
input.onButtonPressed(Button.B, function () {
    if (settingMode) {
        settingField = settingField + 1
        if (settingField == 1) {
            basic.showString("MIN")
        } else if (settingField == 2) {
            basic.showString("SEC")
        } else {
            // All fields set - start the clock
            settingMode = false
            lastTickTime = input.runningTime()
            basic.showString("GO")
        }
    }
})

// --- BUTTON A + B ---
// Running mode: reset back to time-setting mode
input.onButtonPressed(Button.AB, function () {
    if (!settingMode) {
        settingMode = true
        settingField = 0
        hours = 0
        minutes = 0
        seconds = 0
        basic.showString("HR")
    }
})

// --- MAIN LOOP ---
// Counts one second at a time using runningTime() to avoid drift
basic.forever(function () {
    if (!settingMode) {
        let now = input.runningTime()
        if (now - lastTickTime >= 1000) {
            lastTickTime = lastTickTime + 1000
            seconds = seconds + 1
            if (seconds >= 60) {
                seconds = 0
                minutes = minutes + 1
                if (minutes >= 60) {
                    minutes = 0
                    hours = (hours + 1) % 24
                }
            }
        }
        basic.pause(50)
    } else {
        basic.pause(100)
    }
})

// Show the first prompt when the micro:bit powers on
basic.showString("HR")
