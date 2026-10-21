"""Everything he can say — port of Dialogue.swift. All lines original, offline."""
from __future__ import annotations

from enum import auto
from typing import Dict, List, Optional

from .rng import SeededRandom
from .types import AutoName
from .world import FileKind


class LineCategory(AutoName):
    idle = auto(); pockets = auto(); bored = auto(); stare = auto(); cursor = auto()
    panic = auto(); panicRecover = auto(); glassWall = auto(); sleepWake = auto(); dramaticWake = auto()
    work = auto(); celebrate = auto(); clicked = auto(); clickedAgain = auto(); pickedUp = auto()
    dropped = auto(); moved = auto()
    pushWindow = auto(); pushWindowAfter = auto(); escape = auto(); fakeOutStart = auto()
    fakeOutAbort = auto(); meetingClose = auto()
    fourthWall = auto(); knockScreen = auto(); ceiling = auto(); faint = auto(); moonwalk = auto()
    resizedBigger = auto(); resizedSmaller = auto(); screenChanged = auto()
    mood = auto()
    thrown = auto(); dizzy = auto(); ledge = auto(); jumpDown = auto(); landedOnWindow = auto(); rideWindow = auto()
    hungry = auto(); smellFood = auto(); eatPizza = auto(); eatCoffee = auto(); eatDonut = auto()
    ballSpotted = auto(); kickBall = auto(); boredOfBall = auto(); hyper = auto(); tired = auto()
    focusStart = auto(); focusEnd = auto(); breakStart = auto(); breakEnd = auto(); focusPoke = auto()
    awayAsleep = auto(); welcomeBack = auto(); lowBattery = auto(); pluggedIn = auto()
    morning = auto(); lunch = auto(); lateNight = auto(); friday = auto(); weekend = auto()
    greetingMorning = auto(); greetingAfternoon = auto(); greetingEvening = auto(); greetingNight = auto()
    fileHover = auto(); fileImage = auto(); filePdf = auto(); fileCode = auto(); fileArchive = auto()
    fileAudio = auto(); fileVideo = auto(); fileText = auto(); fileSpreadsheet = auto()
    filePresentation = auto(); fileFolder = auto(); fileApp = auto(); fileOther = auto(); fileMany = auto()
    dealWithIt = auto(); partyHat = auto(); achievement = auto()
    ropeThrow = auto(); ropeTug = auto(); ropeArrive = auto(); rappel = auto(); ropeSnap = auto(); noWindows = auto()
    keepFile = auto(); keepMany = auto(); clipboardSaved = auto(); whichOne = auto(); pocketEmpty = auto()
    handOverFile = auto(); handOverClip = auto(); newLook = auto()
    pocketedHeavy = auto(); reminderIntro = auto(); reminderMissed = auto(); reminderDismissed = auto()
    reminderSet = auto()
    binShot = auto(); tidyUp = auto(); binForget = auto()
    cpuSpike = auto(); ramCritical = auto()
    tooManyApps = auto(); tooManyApps15 = auto(); tooManyApps20 = auto()
    appXcode = auto(); appZoom = auto(); appSlack = auto(); appFigma = auto()
    buildSuffering = auto()
    lateNightBed = auto(); mondaySigh = auto(); fridayHype = auto()
    screenTime2h = auto(); screenTime4h = auto(); screenTime6h = auto()
    clipboardUrl = auto(); clipboardTrace = auto(); clipboardError = auto()
    battery20 = auto(); battery10 = auto(); batteryTimer = auto()
    midnightZoomies = auto(); floorNap = auto(); existentialEdge = auto(); selfDestructBluff = auto()
    dizzySpin = auto(); victoryLap = auto(); cursorTag = auto()
    windowCleaning = auto(); edgeKnock = auto(); hidePeek = auto()
    wallPhase = auto(); gravityTest = auto(); phantomTyping = auto(); measureScreen = auto()
    pushUps = auto(); jumpingJacks = auto(); airGuitar = auto(); shadowBoxing = auto(); backflip = auto()
    wiggleDance = auto(); neckCrack = auto(); disappointedShake = auto(); slowWave = auto(); fakePhoneCall = auto()
    flexPose = auto(); tripNothing = auto(); paranoidLook = auto(); jumpScareSelf = auto()

    @staticmethod
    def for_file(kind: FileKind) -> "LineCategory":
        return {
            FileKind.image: LineCategory.fileImage,
            FileKind.pdf: LineCategory.filePdf,
            FileKind.code: LineCategory.fileCode,
            FileKind.archive: LineCategory.fileArchive,
            FileKind.audio: LineCategory.fileAudio,
            FileKind.video: LineCategory.fileVideo,
            FileKind.text: LineCategory.fileText,
            FileKind.spreadsheet: LineCategory.fileSpreadsheet,
            FileKind.presentation: LineCategory.filePresentation,
            FileKind.folder: LineCategory.fileFolder,
            FileKind.app: LineCategory.fileApp,
            FileKind.other: LineCategory.fileOther,
            FileKind.many: LineCategory.fileMany,
        }[kind]


_L = LineCategory
LINES: Dict[LineCategory, List[str]] = {
    _L.idle: ["I was about to do something productive.", "Promotion pending.", "I need a coffee break.",
              "Another day, another nothing.", "Living the dream. Someone else's."],
    _L.pockets: ["Still no money in here.", "Pocket lint. My only asset.", "I had a snack in here in 2019."],
    _L.bored: ["I need a coffee break.", "Is it Friday yet?", "I've been bored for minutes.",
               "Wake me up when it's lunch."],
    _L.stare: ["Are you supervising me?", "Can I help you?", "Don't you have work to do?"],
    _L.cursor: ["Are you supervising me?", "Please respect my personal space.", "That arrow is very pointy.",
                "I see you, little arrow."],
    _L.panic: ["Personal space!", "Not the arrow!", "I'm too unemployed to die!", "Nope nope nope."],
    _L.panicRecover: ["That was intentional.", "I meant to do that.", "Cardio. That was cardio."],
    _L.glassWall: ["Let me out. I have rights.", "Who installed glass here?", "Hello? Outside? Anyone?",
                   "This is a load-bearing wall."],
    _L.sleepWake: ["Five more minutes.", "Was I asleep? I was meditating.", "Huh? I'm up. I'm working."],
    _L.dramaticWake: ["I WAS NOT ASLEEP.", "WHO TOUCHED ME?", "I'M UP! I'M PRODUCTIVE!", "AAAH! Oh. It's you."],
    _L.work: ["Synergizing.", "Typing very important things.", "Circling back. Touching base.",
              "Disrupting the industry."],
    _L.celebrate: ["I have completed absolutely nothing.", "Nailed it.", "Employee of the month. Again.",
                   "Somebody frame this moment."],
    _L.clicked: ["Ow.", "Did we really need another bug?", "Hey. Hands to yourself.", "That tickles. Professionally.",
                 "Please respect my personal space.", "I'm on break."],
    _L.clickedAgain: ["Stop poking the employee.", "I will file a complaint.", "Okay, that's harassment now."],
    _L.pickedUp: ["Whoa whoa whoa!", "Put me down!", "I'm not a mouse!", "Unhand me!"],
    _L.dropped: ["Stop moving the furniture.", "My knees!", "That was intentional.", "A little warning next time?"],
    _L.moved: ["Who rearranged my apartment?", "New neighborhood. Same rent: zero.", "Stop moving the furniture."],
    _L.pushWindow: ["This window is stuck.", "If I push hard enough…", "Come on, open up!"],
    _L.pushWindowAfter: ["…I moved the whole room.", "Okay. The room comes with me.", "Progress. Technically."],
    _L.escape: ["No exit. Not even a fire door.", "Escape route: pending.", "I'll need a smaller screwdriver.",
                "These pixels are sealed tight."],
    _L.fakeOutStart: ["Oh! A friend!", "Wait, is that a treat?", "Hey, buddy!"],
    _L.fakeOutAbort: ["…never mind.", "Nope. Changed my mind.", "Actually, that's work. Pass."],
    _L.meetingClose: ["Great meeting. Same time never.", "Let's take this offline.", "Action items: none. Perfect."],
    _L.fourthWall: ["I know you can see me.", "Nice wallpaper. Did you pick that?", "I live in your RAM, by the way.",
                    "Your tabs are judging you.", "I'm rendered at 30 frames a second, and I'm tired.",
                    "Do you ever close apps, or…?", "Is it cold out there in the real world?",
                    "Tell your browser I said hi."],
    _L.knockScreen: ["Hello? Is this thing on?", "Knock knock. Let me out.",
                     "Can you hear me through the glass?"],
    _L.ceiling: ["Is that the menu bar? Who lives up there?", "The ceiling is full of icons.",
                 "I hear footsteps in the menu bar."],
    _L.faint: ["I'm fine. Pixels are fine.", "Too much screen time."],
    _L.moonwalk: ["Smooth.", "Nobody saw that."],
    _L.resizedBigger: ["I feel taller. Promotion?", "Whoa. Growth spurt.", "Finally, some respect."],
    _L.resizedSmaller: ["Did I just shrink? Is this a demotion?", "Hey! Put my pixels back!", "I feel… compressed."],
    _L.screenChanged: ["Did the world just change size?", "Who moved the walls?", "New resolution, who dis?"],
    _L.mood: ["This is an unpaid internship.", "I'm in my quiet-quitting era.", "Mood: undecided."],
    _L.thrown: ["WHEEEE— I mean, how dare you!", "I'M NOT AERODYNAMIC!", "Workplace safety violation!",
                "Tell my plants I loved them!"],
    _L.dizzy: ["The room is spinning.", "Which one of you threw me?", "I've seen the face of the Dock.",
               "Again! No wait. Never again."],
    _L.ledge: ["That's a long way down.", "I'm not paid enough for heights.", "Nope. Not jumping."],
    _L.jumpDown: ["Geronimo!", "Parkour!", "Hold my coffee!"],
    _L.landedOnWindow: ["Penthouse suite. Nice.", "Great view from up here.", "I'm on top of your work now.",
                        "Is this window load-bearing?"],
    _L.rideWindow: ["Whoa, earthquake!", "Smooth ride. Five stars.", "Are we moving?"],
    _L.hungry: ["I could eat a mouse. The computer kind.", "Is there a fridge in this app?",
                "My stomach is filing a bug report.", "Snack budget: zero. Snack needs: infinite."],
    _L.smellFood: ["Do I smell pizza?", "Food! Wake up, legs!", "Is that for me?"],
    _L.eatPizza: ["Mmm. Tastes like pixels.", "This is the best day of my career.",
                  "Who ordered pizza? Me. Spiritually."],
    _L.eatCoffee: ["Coffee! I CAN SEE SOUNDS!", "Productivity mode: theoretically on!",
                   "Ten more of these and I'll get a job!"],
    _L.eatDonut: ["A donut. Circular, like my career.", "Sweet. Literally.", "Calories don't count in RAM."],
    _L.ballSpotted: ["Ooh, a ball!", "Sports! I'm an athlete now.",
                     "Finally, something to do that isn't work."],
    _L.kickBall: ["GOAL!", "And the crowd goes mild!", "Who needs a goalkeeper?"],
    _L.boredOfBall: ["Okay, I'm retired from sports.", "That's enough cardio for a year."],
    _L.hyper: ["I'm vibrating at a frequency!", "Let's DO things! Any things!", "Who needs sleep? Not me! Ever!"],
    _L.tired: ["My battery is lower than yours.", "I need a nap from my nap.", "Running on fumes. And spite."],
    _L.focusStart: ["Focus mode. I'll be very quiet. Ish.", "Go. Be productive. I'll supervise.",
                    "Deep work time. I'll do shallow work."],
    _L.focusEnd: ["Session complete! I'll take the credit.", "You did it! We did it. Mostly you.",
                  "Great work. I'll put it on my résumé."],
    _L.breakStart: ["Break time. Stretch your legs. I'll stretch mine.",
                    "Look away from the screen. Not at me. Away.",
                    "Hydrate. That's an order. From an intern."],
    _L.breakEnd: ["Break's over. Back to work. You, not me.", "Recess is over, champ."],
    _L.focusPoke: ["Shh. You're supposed to be focusing.", "Eyes on your work!",
                   "I'm not a distraction. I'm a feature."],
    _L.awayAsleep: ["Finally. Some privacy.", "They left. Nap o'clock."],
    _L.welcomeBack: ["Oh! You're back. I was… working.", "Welcome back! Nothing happened. Nothing.",
                     "I definitely didn't nap. Look at my face.", "You were gone forever. Like, minutes."],
    _L.lowBattery: ["We're running out of power! Do something!",
                    "I can see the light… it's the low battery warning.",
                    "Plug us in! I'm too young to sleep forever!"],
    _L.pluggedIn: ["Ahh. Electricity.", "Sweet, sweet power.", "Tastes like lightning."],
    _L.morning: ["Too early for this.", "Morning. My contract says I start at noon.",
                 "Did you bring coffee? For me?"],
    _L.lunch: ["Lunch break? I've been on break since nine.", "Is it lunch? It feels like lunch."],
    _L.lateNight: ["Go to bed. I'll guard the desktop.", "It's late. Even the cursor looks tired.",
                   "Burning the midnight oil? I'm burning nothing."],
    _L.friday: ["It's Friday. My most productive day off.", "Friday! Time to not work, but faster."],
    _L.weekend: ["Working on a weekend? Couldn't be me.", "It's the weekend. Why are we here?"],
    _L.greetingMorning: ["Good morning. Rent is still not due.", "Morning! I missed you. Barely."],
    _L.greetingAfternoon: ["Good afternoon. I was just about to start.", "Oh hey. Afternoon already?"],
    _L.greetingEvening: ["Evening. Long day? Mine was short.", "Good evening. I did nothing. You're welcome."],
    _L.greetingNight: ["It's the middle of the night. Hi?", "Night shift! My favorite. Sleeping shift."],
    _L.fileHover: ["What's that?", "Is that for me?", "Ooh, a delivery."],
    _L.fileImage: ["A picture! Am I in it? No? Pass.", "Nice photo. Needs more goblin.",
                   "I'd frame it, but I'm unemployed."],
    _L.filePdf: ["A PDF. I don't read. I skim.", "Is this a contract? I'm not signing.",
                 "Forty pages? I'll read the title."],
    _L.fileCode: ["Code! Did we really need another bug?", "Looks fine. Ship it. Don't test it.",
                  "I see a semicolon. My work here is done."],
    _L.fileArchive: ["A zip. It's like a present. A boring one.", "Compressed. Like my salary."],
    _L.fileAudio: ["Is this my theme song?", "I'd dance, but I'm on break."],
    _L.fileVideo: ["A movie? Got popcorn?", "I'll watch it later. Never, probably."],
    _L.fileText: ["Words. So many words.", "Did you write me a letter? Aww."],
    _L.fileSpreadsheet: ["A spreadsheet. My natural predator.", "Cell A1 says: no."],
    _L.filePresentation: ["Slides! I'll present them. Badly.", "Next slide, please. No? Okay."],
    _L.fileFolder: ["A whole folder? That's homework.", "I don't open folders. Folders open me."],
    _L.fileApp: ["An app? Is this my new roommate?", "Another app? I was here first."],
    _L.fileOther: ["I have no idea what this is.", "Interesting. Useless, but interesting."],
    _L.fileMany: ["That's a lot of files. I'm overwhelmed.", "Whoa! One at a time!"],
    _L.dealWithIt: ["Deal with it.", "Too cool for this desktop.", "Shades on. Work off."],
    _L.partyHat: ["Party time!", "It's somebody's birthday. Probably."],
    _L.achievement: ["Put that on my performance review!", "Another award. I'm basically famous."],
    _L.ropeThrow: ["Hold my rope.", "Time for some light trespassing.", "Grappling hook: engaged.",
                   "I've seen this in movies."],
    _L.ropeTug: ["Seems sturdy.", "If this breaks, I'm suing.", "Tug test: passed. Probably."],
    _L.ropeArrive: ["The view from up here!", "I conquered a window.", "Base camp reached.", "Upward mobility!",
                    "Now I'm management."],
    _L.rappel: ["Going down!", "Rappelling. Very professional.", "Exit strategy: rope."],
    _L.ropeSnap: ["MY ROPE!", "Who closed that?!", "Rope's gone. So am I!"],
    _L.keepFile: ["I'll keep this safe. Ish.", "Into the pocket it goes.", "Filed. Under 'pocket'.",
                  "Got it. Ask me for it anytime."],
    _L.keepMany: ["That's a lot of paperwork. Pocketed.", "My pocket is getting heavy.",
                  "I'm basically a filing cabinet now."],
    _L.clipboardSaved: ["Copied! I saved that.", "I'll remember that for you.", "Pocketed your copy.",
                        "Got it. Clipboard backup: me."],
    _L.whichOne: ["Which one do you need?", "Okay, what are we looking for?", "Pick one. I kept them all."],
    _L.pocketEmpty: ["My pocket is empty. Just lint.", "Nothing in here. Give me a file!"],
    _L.handOverFile: ["Here you go. Don't lose it.", "Delivered. Tip not included.", "One file, as requested."],
    _L.handOverClip: ["Copied it back. Paste away!", "It's on your clipboard. Ctrl+V time.", "Here's your text."],
    _L.newLook: ["New look. Who dis?", "Do I look different? I feel different.",
                 "Fresh outfit. Same unemployment."],
    _L.pocketedHeavy: ["Pocketed. My back hurts.", "It fits. Somehow.", "I need a chiropractor."],
    _L.reminderIntro: ["Psst! You asked me to remind you!", "Hey! Reminder time!", "Ahem. Official reminder:"],
    _L.reminderMissed: ["You missed this one while I was out:", "Late reminder, but here it is:"],
    _L.reminderDismissed: ["Reminder delivered. You're welcome.", "My work here is done.",
                           "Invoice for reminding you: $0."],
    _L.reminderSet: ["Noted. I'll yell at you later.", "Reminder set. I never forget. Mostly.",
                     "Got it. I'll hold up a sign."],
    _L.binShot: ["Nice shot!", "Three points!", "Swish.", "Straight in the bin!"],
    _L.tidyUp: ["Cleaning up. Don't get used to it.", "Trash day!", "Tidy desk, tidy mind. Allegedly.",
                "I do chores now. Apparently."],
    _L.binForget: ["Forgotten. Your actual file is safe.", "Out of my pocket. Not deleted, relax."],
    _L.noWindows: ["Nothing to climb. Open a window!", "No windows? I'll just stand here then."],
    _L.cpuSpike: ["Is your computer… sprinting?", "Fan's screaming. You're welcome.",
                  "80% CPU. Whatever you're doing, stop.", "The thermal paste is suffering.",
                  "That's not multitasking, that's chaos."],
    _L.ramCritical: ["I can FEEL the swap file.", "Memory pressure: critical. Me: also critical.",
                     "The fans have a message. It's unprintable.", "You've opened too many tabs. In your career.",
                     "Something is about to crash. Probably everything."],
    _L.tooManyApps: ["Ten open apps. This is a cry for help.",
                     "At what point does 'multitasking' become 'chaos'?",
                     "Every one of those apps is judging you."],
    _L.tooManyApps15: ["Fifteen apps. I'm logging this.", "Your RAM called. It's not coming back.",
                       "Fifteen open apps and a to-do list labeled 'important', probably."],
    _L.tooManyApps20: ["TWENTY apps. I refuse to be associated with this.",
                       "At this point you're just collecting apps.", "This computer didn't train for this."],
    _L.appXcode: ["Xcode again. I'll pray for you.", "Brave. Opening Xcode on a day that was going so well.",
                  "Xcode is open. Good luck with the indexing."],
    _L.appZoom: ["Zoom. The meeting that should've been an email.",
                 "You're on Zoom. I'll be very quiet. Nope, nevermind.", "Camera on? You're wearing that?"],
    _L.appSlack: ["Slack notification: someone is wrong on the internet.", "Slack opened. There goes another hour.",
                  "Checking Slack? It's never good news."],
    _L.appFigma: ["Figma. The design will be ready in never.", "You're designing something. I have notes.",
                  "Figma. The pixels are wrong. They're always wrong."],
    _L.buildSuffering: ["Build started. I'll wait here. Forever, apparently.",
                        "Compiling. The universal experience of staring and hoping.",
                        "Xcode is 'building'. Go get coffee. Come back tomorrow.",
                        "Build in progress. The slowness is a feature."],
    _L.lateNightBed: ["It's past 2am. The bed is free, FYI.", "Your future self hates you right now.",
                      "Go to bed. I'll still be here. Unfortunately.",
                      "Nobody productive works this late. I'm just saying."],
    _L.mondaySigh: ["Monday. I had such a good weekend being idle.", "Monday again. *sigh*",
                    "Good morning. It's Monday. I'm sorry."],
    _L.fridayHype: ["It's Friday! Pack it up.", "Friday! The logs can wait until Monday.",
                    "Technically the weekend has begun. I'm just saying."],
    _L.screenTime2h: ["You've been at this for 2 hours. Stand up.", "Two hours. Your neck is making a noise.",
                      "Blink. That was a reminder."],
    _L.screenTime4h: ["Four hours. Your eyes are square.",
                      "You've sat here for four hours. That's a flight to London.",
                      "Halfway through the day and you haven't moved. Impressive. Terrible."],
    _L.screenTime6h: ["Six hours. The sun has moved since you sat down.",
                      "SIX HOURS? Are you okay? Don't answer, just stand up.",
                      "This is not a healthy relationship with a screen."],
    _L.clipboardUrl: ["Copied a URL. Probably a rabbit hole you'll regret.",
                      "That link will be open in seventeen tabs by tomorrow.",
                      "A URL. Somewhere in there is 40 minutes of your life."],
    _L.clipboardTrace: ["Stack trace! Classic. Classic mistake.", "You copied a stack trace. That's commitment.",
                        "Ah. The error was real. Respect."],
    _L.clipboardError: ["Error code. Great. Google time.", "Copying error codes. The programmer experience.",
                        "That error code has been googled 47,000 times. You're in good company."],
    _L.battery20: ["Twenty percent. Not a crisis. Yet.", "Battery at 20. Plug in before we get dramatic.",
                   "Gentle reminder: a charger exists."],
    _L.battery10: ["TEN PERCENT. WE ARE DYING.", "Plug in. NOW. I mean it. NOW.",
                   "Ten percent battery! I have unfinished business!"],
    _L.batteryTimer: ["Less than 30 minutes left. This is a countdown.",
                      "We're running out of battery. Like, actual minutes.",
                      "Find a charger. Any charger. A wall, a car, ANYTHING."],
    _L.midnightZoomies: ["I needed that.", "I can explain. No I can't.", "No notes.",
                         "That was purely professional."],
    _L.floorNap: ["I wasn't asleep. I was horizontal.", "Nap complete. I'm exactly as rested.",
                  "Floor nap: 10/10.", "The floor is cooler down here."],
    _L.existentialEdge: ["Sometimes I just sit here and think about nothing.",
                         "This is where I come to not answer emails.", "The void. Looks about right.",
                         "It's a big screen and I'm just standing on part of it."],
    _L.selfDestructBluff: ["Nah.", "Changed my mind.", "Just kidding. Mostly."],
    _L.dizzySpin: ["I spun. I regret it.", "Physics: confirmed.", "That was a choice.",
                   "Zero stars. Would not spin again."],
    _L.victoryLap: ["No reason. Don't ask.", "Lap one of one. Complete.",
                    "The real victory was the running we did along the way.", "Official lap: logged."],
    _L.cursorTag: ["Tag! You're it. You'll never catch me.", "Touched it. My work here is done.",
                   "That arrow was asking for it.", "IT."],
    _L.windowCleaning: ["Still dirty. Some stains are forever.", "I cleaned it. Barely.",
                        "Clean-ish. I'm not getting paid for this.", "The screen is mostly clean. Probably."],
    _L.edgeKnock: ["Nobody home. As expected.", "Knocked. Zero response. Typical.",
                   "I knocked. They heard. They chose silence.", "No answer. I'll try again in never."],
    _L.hidePeek: ["I see everything from here.", "Hiding successfully. Nobody suspects.",
                  "Best hiding spot on the desktop.", "You can't see me. This is science."],
    _L.wallPhase: ["Physics is more of a suggestion, really.", "Shortcut. I found a shortcut.",
                   "The wall and I have an understanding.", "I did a thing. Walls don't apply to me."],
    _L.gravityTest: ["Hypothesis: floor is still down there. Testing.",
                     "I'm going to do something and I need you to not react.", "Scientific purposes.",
                     "For science. Definitely for science."],
    _L.phantomTyping: ["Email sent. Probably. I have no email.", "Submitted. Whatever it was.",
                       "My invisible keyboard has better tactile feedback than most real ones.",
                       "Work completed. It was hypothetical work."],
    _L.measureScreen: ["Data collected. Report: it's wide.", "Walked it. Clocked it. Filed it.",
                       "Results: too much space, still not enough for me.",
                       "Measurements complete. I'll invoice you."],
    _L.pushUps: ["Three push-ups. I'm basically an athlete.", "That's my workout. Until next year.",
                 "I can do more. I choose not to.", "Fitness unlocked. Mostly."],
    _L.jumpingJacks: ["Jacks one through four. Done.", "Cardio. I do that sometimes.",
                      "I'd high-five you but my arms are tired."],
    _L.airGuitar: ["You didn't hear that riff? Your loss.", "Solo complete. Album drops never.",
                   "I am the band and the audience."],
    _L.shadowBoxing: ["Shadow: defeated. Again.", "The shadow never learns.",
                      "Undefeated. My shadow is 0 and counting."],
    _L.backflip: ["Nailed it. Don't rewind.", "Technically that was a backflip.", "The landing was intentional."],
    _L.wiggleDance: ["Don't ask me why. Don't.", "This is what peak performance looks like.",
                     "The music is in my head. It's good."],
    _L.neckCrack: ["Ah.", "That was necessary.", "I was carrying that since 2023."],
    _L.disappointedShake: ["I just… I expected better.", "You know what you did.",
                           "I'm not angry. Just deeply, deeply tired.", "This is my 'not surprised' face."],
    _L.slowWave: ["I waved. Nothing.", "Hi. ...Hi. ...Okay.", "Wave acknowledged. Zero response. Fine."],
    _L.fakePhoneCall: ["Nobody called. I just needed a moment.", "The call was made up. The outcome was real.",
                       "My contact list has zero contacts."],
    _L.flexPose: ["Peak physical form. As you can see.", "Zero gym required.",
                  "I've been working out. In my mind."],
    _L.tripNothing: ["The floor was uneven. At a pixel level.", "There was definitely something there.",
                     "I meant to do that.", "Invisible obstacle. Very dangerous."],
    _L.paranoidLook: ["...nothing. As I suspected.", "I heard something. Probably pixels.", "Clear. For now."],
    _L.jumpScareSelf: ["My own shadow. My natural predator.", "That was my shadow. We're fine.",
                       "I spooked myself. This is fine."],
}


def lines_for(category: LineCategory) -> List[str]:
    return LINES.get(category, [])


MEETING_PAIRS = [
    ("Agenda item one: nothing.", "Seconded."),
    ("Who approved this?", "You did."),
    ("Any blockers?", "The glass."),
    ("Can we circle back?", "We're going in circles."),
    ("Status update?", "Still trapped."),
    ("Budget?", "Zero. As usual."),
    ("Should we hire someone?", "Hire us. Twice."),
]


class DialogueDirector:
    """Picks lines with cooldowns so he doesn't repeat himself or talk constantly."""

    def __init__(self):
        self.global_gap = 7.0
        self.no_repeat_window = 14
        self.category_gap = 20.0
        self.talkativeness = 0.6
        self._last_spoken_at = float("-inf")
        self._last_by_category: Dict[LineCategory, float] = {}
        self._recent: List[str] = []

    def line(self, category: LineCategory, now: float, rng: SeededRandom,
             chance: float = 1.0, force: bool = False) -> Optional[str]:
        if not force:
            if self.talkativeness <= 0:
                return None
            if now - self._last_spoken_at < self.global_gap:
                return None
            last = self._last_by_category.get(category)
            if last is not None and now - last < self.category_gap:
                return None
            scaled = min(1.0, chance * (0.35 + self.talkativeness * 1.1))
            if not rng.chance(scaled):
                return None
        pool = lines_for(category)
        options = [s for s in pool if s not in self._recent]
        if not options:
            last = self._recent[-1] if self._recent else None
            options = [s for s in pool if s != last]
        if not options:
            return None
        text = rng.choice(options)
        self.record(text, category, now)
        return text

    def record(self, text: str, category: Optional[LineCategory], now: float) -> None:
        self._last_spoken_at = now
        if category is not None:
            self._last_by_category[category] = now
        self._recent.append(text)
        if len(self._recent) > self.no_repeat_window:
            self._recent = self._recent[len(self._recent) - self.no_repeat_window:]

    @property
    def recent_lines(self) -> List[str]:
        return list(self._recent)
