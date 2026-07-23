"""FBS team directory for 247Sports Crystal Ball.

Each entry: (display name, 247 college slug). The slug is what goes in the
URL: https://247sports.com/college/<slug>/Season/2027-Football/currenttargetpredictions/

Slugs follow a consistent pattern (lowercase, spaces -> hyphens). If a slug is
wrong for a given school, the scout handles the 404 gracefully (reports
"no data"). Add/override entries here as needed.
"""

FBS_TEAMS = [
    # ACC
    ("Miami", "miami"), ("Florida State", "florida-state"), ("Clemson", "clemson"),
    ("North Carolina", "north-carolina"), ("NC State", "nc-state"), ("Virginia Tech", "virginia-tech"),
    ("Virginia", "virginia"), ("Pitt", "pitt"), ("Syracuse", "syracuse"),
    ("Boston College", "boston-college"), ("Wake Forest", "wake-forest"),
    ("Georgia Tech", "georgia-tech"), ("Duke", "duke"), ("Louisville", "louisville"),
    ("California", "california"), ("Stanford", "stanford"), ("SMU", "smu"),
    # SEC
    ("Alabama", "alabama"), ("Georgia", "georgia"), ("Texas", "texas"),
    ("LSU", "lsu"), ("Tennessee", "tennessee"), ("Texas A&M", "texas-am"),
    ("Ole Miss", "ole-miss"), ("Auburn", "auburn"), ("South Carolina", "south-carolina"),
    ("Kentucky", "kentucky"), ("Missouri", "missouri"), ("Arkansas", "arkansas"),
    ("Mississippi State", "mississippi-state"), ("Florida", "florida"), ("Vanderbilt", "vanderbilt"),
    ("Oklahoma", "oklahoma"), ("Texas Tech", "texas-tech"),
    # Big Ten
    ("Ohio State", "ohio-state"), ("Michigan", "michigan"), ("Penn State", "penn-state"),
    ("Oregon", "oregon"), ("USC", "usc"), ("Washington", "washington"),
    ("UCLA", "ucla"), ("Wisconsin", "wisconsin"), ("Iowa", "iowa"),
    ("Nebraska", "nebraska"), ("Michigan State", "michigan-state"), ("Minnesota", "minnesota"),
    ("Indiana", "indiana"), ("Purdue", "purdue"), ("Northwestern", "northwestern"),
    ("Illinois", "illinois"), ("Rutgers", "rutgers"), ("Maryland", "maryland"),
    ("Iowa State", "iowa-state"), ("Kansas", "kansas"), ("Kansas State", "kansas-state"),
    ("Colorado", "colorado"), ("Utah", "utah"), ("Arizona", "arizona"),
    ("Arizona State", "arizona-state"), ("Oklahoma State", "oklahoma-state"),
    ("Baylor", "baylor"), ("TCU", "tcu"), ("West Virginia", "west-virginia"),
    ("Houston", "houston"), ("Cincinnati", "cincinnati"),
    ("BYU", "byu"), ("UCF", "ucf"),
    # Independent / others
    ("Notre Dame", "notre-dame"), ("Army", "army"), ("Navy", "navy"),
    ("Air Force", "air-force"), ("Connecticut", "connecticut"), ("Umass", "umass"),
    # American / G5 powers
    ("Memphis", "memphis"), ("Tulane", "tulane"), ("East Carolina", "east-carolina"),
    ("Boise State", "boise-state"), ("Fresno State", "fresno-state"),
    ("San Diego State", "san-diego-state"), ("Wyoming", "wyoming"),
    ("Colorado State", "colorado-state"), ("Utah State", "utah-state"),
    ("Appalachian State", "appalachian-state"), ("Coastal Carolina", "coastal-carolina"),
    ("Louisiana", "louisiana"), ("Louisiana Tech", "louisiana-tech"),
    ("Arkansas State", "arkansas-state"), ("South Alabama", "south-alabama"),
    ("Georgia Southern", "georgia-southern"), ("Georgia State", "georgia-state"),
    ("Troy", "troy"), ("James Madison", "james-madison"), ("Old Dominion", "old-dominion"),
    ("Charlotte", "charlotte"), ("Middle Tennessee", "middle-tennessee"),
    ("Western Kentucky", "western-kentucky"), ("UTSA", "utsa"), ("North Texas", "north-texas"),
    ("Rice", "rice"), ("UNT", "unt"), ("FAU", "fau"), ("FIU", "fiu"),
    ("Liberty", "liberty"), ("Sam Houston", "sam-houston"),
    ("Jacksonville State", "jacksonville-state"), ("Kennesaw State", "kennesaw-state"),
    ("New Mexico State", "new-mexico-state"), ("UTEP", "utep"),
]


def team_by_slug(slug):
    for name, s in FBS_TEAMS:
        if s == slug:
            return name
    return slug


def all_teams():
    return [{"name": n, "slug": s} for n, s in FBS_TEAMS]
