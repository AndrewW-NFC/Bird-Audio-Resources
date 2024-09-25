A collection of bird audio resources, with an emphasis on nocturnal flight call recording.

* My eBird account: [Andrew W. - NFCs/Remote field audio](https://ebird.org/profile/NjIxMzM1Nw/world)
* My uploaded recordings: [macaulaylibrary.org](https://search.macaulaylibrary.org/catalog?userId=USER6213357)
* Similar document: ["Bibliography of Nocturnal Flight Call Sources"](https://docs.google.com/document/d/1YaKaqGodIJnhLMBfQTJAxRnk9Cb4qoE4H1syjpL1Otg/edit?fbclid=IwY2xjawFa6aZleHRuA2FlbQIxMAABHbxYmn7XsiKwD7ot-3ie1P-bniEka6qCcxwdQRuaiORQHy7j4bTmYfiAmA_aem_-5hW-eN4yluYl_Hctfh3hw) assembled by Joe Gyekis and Julia Plummer

# Low-cost recorders
## For purchase
* AudioMoth: [openacousticdevices.info/audiomoth](https://openacousticdevices.info/audiomoth).
* BirdWeather PUC: [birdweather.com](https://birdweather.com). Explore the 1,700+ BirdWeather stations, mostly in North America and Europe: [app.birdweather.com](https://app.birdweather.com). This device, which makes live identifications using the BirdNET API, is good for passive monintoring and recording of bird calls but has not proven effective for nocturnal flight calls. See "BirdNET API" below as to why.
## DIY (with a purchase option)
* [OldBird 21c](http://oldbird.org)

# My borrowed higher-quality recording equipment
* [MixPre-3 preamp and recorder](https://www.sounddevices.com/product/mixpre-3/). This is a discontinued model. The current model is the [MixPre-3 II](https://www.sounddevices.com/product/mixpre-3-ii/)
* Sennheiser ME 66 Supercardioid Shotgun Microphone ([PDF](https://assets.sennheiser.com/global-downloads/file/11897/SpecSheet_ME_66_EN.pdf))
* [Zoom F1-SP](https://zoomcorp.com/en/us/field-recorders/field-recorders/f1-sp/) combo recorder and shotgun mic

# Other recording setups at various price-points
* See [Nocturnal Flight Calls Facebook group](https://www.facebook.com/groups/NocturnalFlightCalls/) below

# Guides and Communities
* [Peterson Field Guide to Bird Sounds of Eastern North America](https://harpercollins.com/products/peterson-field-guide-to-bird-sounds-of-eastern-north-america-nathan-pieplow). Includes an introduction on how to read spectrograms and indexes for looking up species by sound qualities. There is an [online version](https://academy.allaboutbirds.org/peterson-field-guide-to-bird-sounds), but it is searchable only by species name, not by sound types or qualities.
* [Nocturnal Flight Calls of North America](https://nocturnalflightcalls.com/): an online reference guide to nocturnal flight call spectrograms
* Facebook group ["Nocturnal Flight Calls"](https://www.facebook.com/groups/NocturnalFlightCalls/). Includes [a thread](https://www.facebook.com/groups/NocturnalFlightCalls/posts/10165508057595436/) about people's different NFC recording setups. The group is set to private, so you must submit a request to join and view content.
* Reddit community: [r/fieldrecording](https://www.reddit.com/r/fieldrecording/). Not specific to bird sound recording but a good resource for recording equipment recommendations and technical advice.
* ["AudioMoth: a practical guide to the open-source ARU"](https://github.com/rhine3/audiomoth-guide/blob/master/guide.md) (ARU = autonomous recording unit)
* [Bill Evans' glossary of bird call terms](http://oldbird.org/pubs/fcmb/pages/glossary.htm)
* [Flowchart](https://github.com/AndrewW-NFC/Bird-Audio-Resources/blob/main/Zeep%20flowchart%20-%20Landborough%20page%2012.jpg) for identifying the difficult "zeep" flight calls

# Nocturnal Migration Forecasting and Alerts
## [BirdCast migration tools](https://birdcast.info/migration-tools)
Use these to help plan for good local NFC nights and to anticipate migrant species:
* [Migration Alerts](https://birdcast.info/migration-tools/local-migration-alerts/) for nights of high predicted migration are active from March 1 until June 15 (spring migration) and August 1 until November 15 (fall migration).
* The [Migration Dashboard](https://birdcast.info/migration-tools/migration-dashboard/) can help you anticipate which species will be passing through.

> [!NOTE]
> * Migration alerts are available only for the continental United States.
> * Alerts are triggered by high overall volume of migrants, regardless of species. This tends to be concentrated in mid-September to mid-October, but bear in mind many species -- especially shorebirds -- migrate earlier than that. If you want to focus on certain species, study their migration timing rather than rely on alerts.

# The eBird NFC protocol
* If you use eBird to track your observations, you should follow [its Nocturnal Flight Call Count protocol](https://support.ebird.org/en/support/solutions/articles/48000950859-guide-to-ebird-protocols#anchorNFC). Remember that eBird checklists ultimately feed into ornithological research; following protocols is essential for researchers to be confident data has been collected in consistent ways. The NFC protocol differs from the more familiar ones in eBird ("stationary", "traveling", and "incidental"). For example, since it's impossible to tally birds while they're flying overhead in the dark, the NFC protocol asks you to count the _number of recorded calls_ and include those counts as species comments. 

# Software
* [Audacity](https://audacityteam.org) for "viewing", listening to, and editing recordings
* [Vesper](https://github.com/RichardLitt/nfc-resources) and [Nighthawk](https://github.com/bmvandoren/Nighthawk), software specifically for analyzing long NFC recording sessions. I've just started with Nighthawk and am excited by it. It can analyze an audio file and generate a spreadsheet of bird sounds it has identified, including the timestamp of the sound and Nighthawk's best guess at the class and species. For Audacity users, Nighthawk can generate a label track -- labeling each sound on the audio track and letting you bulk-export every sound as a separate file.
> [!NOTE]
  > Nighthawk is not designed to analyze songs. Its training data are calls. Don't bother trying to use it to analyze daytime singers.
* [Merlin](https://merlin.allaboutbirds.org/): the go-to bird sound ID app, but it is not suitable for NFCs.
* [BirdNET API](https://birdnet.cornell.edu/api/): web-based bird sound ID. Unless you're using the API for other projects, consider this merely a backup option for Merlin, as its matches aren't filtered by date and location. It is not suitable for NFCs.

> [!NOTE]
> To emphasize: Merlin and BirdNET aren't well-trained on flight calls. They are well-trained for songs and "terrestrial" calls. Assume those platforms will not make positive flight call IDs.

# Audio Repositories
* The Macaulay Library, Cornell University. [This link](https://search.macaulaylibrary.org/catalog?mediaType=audio&tag=flight_call) takes you to a Macaulay search for flight calls, though not necessarily nocturnal flight calls. Keep an eye out for usernames that include "NFC", "NFC Station", etc.
* [Xeno-Canto](https://xeno-canto.org). [This link](https://xeno-canto.org/explore?query=type:%22nocturnal%20flight%20call%22) takes you to a Xeno-Canto search for nocturnal flight calls.

# Skills Development
* [Earbider](https://earbirder.com): Custom sound/sprectogram quizzes, including filtering by flight calls or NFC stations only
* [eBird quizzes](https://ebird.org/quiz): Location- and date-specific quizzes on all bird sounds, not just NFCs.

# Books and Articles
* [_The Singing Life of Birds: The Art and Science of Listening to Birdsong_](https://www.goodreads.com/book/show/6263.The_Singing_Life_of_Birds)
* Textbook: [_The Migration Ecology of Birds_](https://www.goodreads.com/book/show/2138419.The_Migration_Ecology_of_Birds)
* Textbook: [_Bird Song: Biological Themes and Variations_](https://www.goodreads.com/book/show/4579255-bird-song)
* Interdisciplinary academic monograph: [_Listening in the Field: Recording and the Science of Birdsong_](https://www.goodreads.com/book/show/36722601-listening-in-the-field)
* ["Welcome to the Dark Side: Your Guide to Nocturnal Migration Birding"](https://www.audubon.org/magazine/spring-2022/welcome-dark-side-your-guide-nocturnal-migration), _Audubon Magazine_ (Spring 2022)
* ["Here’s How You Go Birding in the Middle of the Night"](https://www.scientificamerican.com/podcast/episode/heres-how-you-go-birding-in-the-middle-of-the-night1/), _Scientific American_ (August 2023)
* [Birding while you sleep: how to get started with noc-mig](https://www.birdguides.com/articles/general-birding/birding-while-you-sleep-how-to-get-started-with-noc-mig/), BirdGuides (June 2020)
* ["Decoding the ‘zeep’ complex: quantitative analysis of interspecific variation in the nocturnal flight calls of nine wood warbler species (Parulidae spp.)"](https://github.com/AndrewW-NFC/Bird-Audio-Resources/blob/main/Landsborough%20-%20Decoding%20the%20%E2%80%98zeep%E2%80%99%20complex.pdf), Landsborough et al. in _Bioacoustics_

# Exemplary Recordings
Would like to find some in addition to Bill's.
* ["Big Migration Night"](https://soundcloud.com/user-830174402/big-migration-night)
* ["Big Migration Night - Harlingen, Texas, USA"](https://soundcloud.com/user-830174402/big-migration-night-harlingen-texas-usa)

# People
* [Bill Evans](https://scholar.google.com/citations?user=XoZ5lP0AAAAJ&hl=en&oi=sra)
* [Benjamin Van Doren](https://www.migrationbiology.org)
* [Joe Gyekis](https://www.youtube.com/user/jgyekis/playlists)
