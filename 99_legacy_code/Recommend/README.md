## How to Use

Put your user history in read_user_log() function in main.py, and run main.py.

- The images of the user history is saved to output/user_log.jpg.
- Five pages of recommendations will be generated and saved as output/Page (page number).jpg.
    - (It assumes that the user does not click on any artworks in each recommendation page.)
    - You can change the number of pages generated and indicate whether user has clicked on any recommended artwork by modifying line 189 of main.py (`for page_idx, if_new_click in enumerate([True, False, False, False, False]):`)

## Recommendation Channels

Four channels have been implemented

### Image Similarity Channel

channels/image_sim.py

- Get image_list: num_image artworks that were most recently clicked by the user.
- Get image_recs_list: the artworks that are visually similar to each of those artworks, respectively.
- Shuffle the first few (shuffle_len) artworks in each result list.

### Common Tags Channel

channels/common_tags.py

- Take the tag_log_len most recent records of the user history.
- Get tag_list: num_tag tags from the records that have the highest click rates.
- Get tag_recs_list: for each of those tags, get all the artworks having this tag, and rank the artworks in the descending order of their total tag scores (= sum of the click rates of all the tags the artwork has that are within the tag_list).

### Same Artist Channel

channels/same_artist.py

- Get artist_list: artist_display fields of the num_artist most recently clicked artworks
- Get artist_recs_list: for each artist, get the artworks having the same artist.

### Random Recommendation Channel

channels/random_rec.py

- Get random_recs_list: randomly select artworks to recommend.

## Generating One Recommendation Page

- Get the recommendation lists from all channels
- Randomly pick a list, and select the first artwork in the list that has not been clicked in the num_interacted most recent records, or recommmended in the num_recommended most recent records.
    - The sampling probability of each recommendation list is adjustable. (`weights` variable)

## Multiple Recommendation Pages Without Clicking

If the user reaches to the end of the current recommendation page (page_rec_len recommendations in total) without clicking any artworks, the next page's recommendations should have a larger degree of randomness.
- The weight of the random recommendation is increased each time the recommender makes a consecutive recommendation without the user clicking on any artworks.
