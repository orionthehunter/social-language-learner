# social-language-learner
An applied solution to the Social Golfer Problem.

Finally got this script working. It took me and ChatGPT with reasoning to make it happen, and even then it took a dozen or so troubleshooting sessions. The script is WAY beyond what I could do alone and I only generally understand how it works. Part of that is because it's calling on two libraries which I don't know how work, pandas and numpy.

Anyway, the point is, this is probably useful for many (language) teachers. It's an applied solution for the Social Golfer problem in language classes where you want to randomize groups with minimal repeated pairings. Specifically the script prioritizes groups of 3, and falls back to groups of 4 when that isn't possible. It gives errors for the low class sizes where that grouping is impossible (i.e. 1, 2, and 5 person classes). Furthermore, it allows you to mark absences by writing the next Iteration header and an "x" in the absent students' rows.

My classes never have more than 11 groups, so I made a list of 11 English tree names to use as the group names. This is easily modifiable in the script.

It takes a .csv file named "roster.csv" formatted as the one shown in roster-template.csv and updates it. The roster.csv file I attached shows example output.

I also had gpt make a separate script to read and report all groupings for each student so far as a matrix, so that you can check the actual cumulative results.
