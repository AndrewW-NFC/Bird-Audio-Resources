# Bird Audio Resources

A curated guide to recording, identifying, and analyzing bird audio, with an emphasis on nocturnal flight calls.

=======
# Code and Software (all free)
* My AppleScript for [automating overnight recordings with Audition](https://github.com/AndrewW-NFC/Bird-Audio-Resources/blob/main/Audition%201-hour%20recordings%20with%20break%20at%20midnight%20and%20enrivonmental%20conditions.scpt). This code starts and stops Audition recordings every hour, with a special stop at midnight, all in order to follow eBird's NFC protocol. It saves each file using a filename that includes the start date and time. It also logs that hour's weather conditions. I'm still experimenting with how to add accurate local precipitation data to the log.
* Generate a local recording quality forecast with [my Python script](https://github.com/AndrewW-NFC/Bird-Audio-Resources/blob/main/NFC%20quality%20weather%20forecast.py) or [my HTML(https://github.com/AndrewW-NFC/Bird-Audio-Resources/blob/main/nfc_recording_forecast_web.html)].
* [Audacity](https://audacityteam.org) for "viewing", listening to, and editing recordings
* [Vesper](https://github.com/RichardLitt/nfc-resources) and [Nighthawk](https://github.com/bmvandoren/Nighthawk), software specifically for analyzing long NFC recording sessions. Nighthawk can analyze an audio file and generate a spreadsheet of bird sounds it has identified, including the timestamp of the sound and Nighthawk's best guess at the class and species. For Audacity users, Nighthawk can generate a label track -- labeling each sound on the audio track and letting you bulk-export every sound as a separate file.
> [!NOTE]
  > Nighthawk is not designed to analyze bird songs. Its training data are calls.
* [Merlin](https://merlin.allaboutbirds.org/): the go-to bird sound ID app, but it is not suitable for NFCs.
* [BirdNET API](https://birdnet.cornell.edu/api/): web-based bird sound ID. Unless you're using the API for other projects, consider this merely a backup option for Merlin, as its matches aren't filtered by date and location. It is not suitable for NFCs.

> [!NOTE]
> Merlin and BirdNET aren't well-trained on flight calls that differ from "terrestial" calls. Though you might get lucky, assume those platforms will not make reliable (or any) flight call IDs.

# Audio Repositories
* The Macaulay Library, Cornell University. [This link](https://search.macaulaylibrary.org/catalog?mediaType=audio&tag=flight_call) takes you to a Macaulay search for flight calls, though not necessarily nocturnal flight calls. Keep an eye out for usernames that include "NFC", "NFC Station", etc.
* [Xeno-Canto](https://xeno-canto.org). [This link](https://xeno-canto.org/explore?query=type:%22nocturnal%20flight%20call%22) takes you to a Xeno-Canto search for nocturnal flight calls.

> [!NOTE]
> NFC folks in Europe tend to use [Trektellen](https://www.trektellen.org/). I need to explore it more but I don't think it supports direct audio uploads; rather, users to link to xeno-canto.

# Skills Development
* [Earbider](https://earbirder.com): Custom sound/sprectogram quizzes, including filtering by flight calls or NFC stations only
* [eBird quizzes](https://ebird.org/quiz): Location- and date-specific quizzes on all bird sounds, not just NFCs.

# Books and Articles
* [A call in the dark: Nocturnal flight calls and their potential to advance the study of avian migration](https://academic.oup.com/auk/advance-article/doi/10.1093/ornithology/ukaf002/7951360)
* [Nighthawk: Acoustic monitoring of nocturnal bird migration in the Americas](https://besjournals.onlinelibrary.wiley.com/doi/full/10.1111/2041-210X.14272)
* [_The Singing Life of Birds: The Art and Science of Listening to Birdsong_](https://www.goodreads.com/book/show/6263.The_Singing_Life_of_Birds)
* Textbook: [_The Migration Ecology of Birds_](https://www.goodreads.com/book/show/2138419.The_Migration_Ecology_of_Birds)
* Textbook: [_Bird Song: Biological Themes and Variations_](https://www.goodreads.com/book/show/4579255-bird-song)
* Interdisciplinary academic monograph: [_Listening in the Field: Recording and the Science of Birdsong_](https://www.goodreads.com/book/show/36722601-listening-in-the-field)
* Academic collection of sound articles: [_The Sound Studies Reader_](https://www.routledge.com/The-Sound-Studies-Reader/Sterne/p/book/9780415771313), ed. Jonathan Sterne
* Academic monograph: [The Audible Past: Cultural Origins of Sound Reproduction](https://www.goodreads.com/book/show/451210.The_Audible_Past), Jonathan Sterne
* ["Welcome to the Dark Side: Your Guide to Nocturnal Migration Birding"](https://www.audubon.org/magazine/spring-2022/welcome-dark-side-your-guide-nocturnal-migration), _Audubon Magazine_ (Spring 2022)
* ["Here’s How You Go Birding in the Middle of the Night"](https://www.scientificamerican.com/podcast/episode/heres-how-you-go-birding-in-the-middle-of-the-night1/), _Scientific American_ (August 2023)
* [Birding while you sleep: how to get started with noc-mig](https://www.birdguides.com/articles/general-birding/birding-while-you-sleep-how-to-get-started-with-noc-mig/), BirdGuides (June 2020)
* ["Decoding the ‘zeep’ complex: quantitative analysis of interspecific variation in the nocturnal flight calls of nine wood warbler species (Parulidae spp.)"](https://github.com/AndrewW-NFC/Bird-Audio-Resources/blob/main/Landsborough%20-%20Decoding%20the%20%E2%80%98zeep%E2%80%99%20complex.pdf), Landsborough et al. in _Bioacoustics_

# Exemplary Recordings
(Would like to find some in addition to Bill's.)
* ["Big Migration Night"](https://soundcloud.com/user-830174402/big-migration-night)
* ["Big Migration Night - Harlingen, Texas, USA"](https://soundcloud.com/user-830174402/big-migration-night-harlingen-texas-usa)

# People
* [Bill Evans](https://scholar.google.com/citations?user=XoZ5lP0AAAAJ&hl=en&oi=sra)
* [Benjamin Van Doren](https://www.migrationbiology.org)
* [Joe Gyekis](https://www.youtube.com/user/jgyekis/playlists)
>>>>>>> parent of 9b24f54 (Update README.md)
