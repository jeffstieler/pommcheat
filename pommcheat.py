#!/home/user/opt/bin/python2.6
# CHANGE THE ABOVE LINE TO THE LOCATION OF YOUR PYTHON EXECUTABLE!

class Point:
	"""A simple x,y point that allows Point - Point subtraction"""
	def __init__(self, x, y):
		self.x, self.y = x, y
		
	def __div__(self, p):
		return Point(self.x / p.x, self.y / p.y)
	
	def __mul__(self, p):
		return Point(self.x * p.x, self.y * p.y)
		
	def __sub__(self, p):
		return Point(self.x - p.x, self.y - p.y)

import urllib, re, os, cgi, cgitb, json, sqlite3

mapURL = "http://howow.linebr.com/pomm/pomm_run.php"
# http://www.conquestofthehorde.com/components/pomm/pomm.php
# http://www.eyes-of-eternity.exano.net/components/pomm/pomm.php?rid=1
# http://wemilktaurens.site88.net/components/pomm/pomm.php
# http://litvivan.game-server.cc/wow/components/pomm/pomm.php
# http://213.141.140.82/wow/components/pomm/pomm.php
bracketRegex = "(\[.*\])"
MAP_WIDTH = 784.00
MAP_HEIGHT = 525.00
ZONE_RATIO_X = 11.02
ZONE_RATIO_Y = 6.68
CHARSET = 'utf8'
DATABASE = './pommcheat.db'
POINT_HTML = '''<a href="#"><img src="img/%s_point.gif" style="position: absolute; left: %spx; top: %spx;" '''
POINT_HTML += '''onmousemove="tip('%s', '%s', '<img src=\\'img/%d-%d.gif\\' style=\\'float: center;\\'/>'''
POINT_HTML += '''<img src=\\'img/%d.gif\\' style=\\'float: center;\\'/><br>%s<br>%s<br>%s');" onmouseout="h_tip();"'''
POINT_HTML += '''onclick="javascript:document.getElementById('charName').value='%s'; reset();" /></a>\n'''

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

conn = sqlite3.connect(DATABASE)
conn.row_factory = dict_factory
cur = conn.cursor()

def TranslatePoint(point, zone):
	cur.execute('select parent, x_offset, y_offset from zones where name = ?', (zone, ))
	zoneData = cur.fetchone()
	if zoneData['parent'] is None:
		cur.execute('select x, y from zones where name = ?', (zone, ))
		dimension = cur.fetchone()
		return Point(((point.x / 100) * dimension['x']), ((point.y / 100) * dimension['y']))
	return TranslatePoint(point, zoneData['parent']) - Point(zoneData['x_offset'], zoneData['y_offset'])

def WebMapCoordsToZoneCoords2(zone, x, y):
	# Coordinates are in proportion to the webmap, get them on a 100,100 scale
	# and make them a Point while we're at it
	position = Point(x * (100 / MAP_WIDTH), y * (100 / MAP_HEIGHT))
	# Get the dimensions of the zone and scale to percentage
	cur.execute('select x, y from zones where name = ?', (zone, ))
	z = cur.fetchone()
	zoneSize = Point(z['x'], z['y']) / Point(100, 100)
	# Account for zone, continent, and 'world' offsets, divide by zone's size to get percentage
	# Then multiple by zone mapsize to get pixel location
	return (TranslatePoint(position, zone) / zoneSize) * Point(ZONE_RATIO_X, ZONE_RATIO_Y)

def parseQueryString():
	"""Pull char and zone parameters from query string"""
	qs = cgi.FieldStorage()
	return({'char': qs.getvalue('char'), 'zone': qs.getvalue('zone')})

def parsePlayerData():
	"""Pull player data from target server, format as valid JSON, return parsed JSON"""
	try:
		rawPlayerData = str(re.findall(bracketRegex, urllib.urlopen(mapURL).read())[0])
	except:
		print "exception!"
		rawPlayerData = None
	if rawPlayerData is not None:
		fixedPlayerData = re.sub("'(\d+)'", '\g<1>', rawPlayerData).replace("\\'", "").replace("'", '"')
		return json.loads(fixedPlayerData, 'latin1')

def getPlayersForZone(players, zone):
    """Filters player list by 'zone' attribute"""
    player = filter(lambda p: p['zone'] != u'Unknown' and p['name'] != u'Dead', players)
    if zone is None: return players
    return filter(lambda p: p['zone'] == zone, players)

# Determine if the player is Horde
def isHorde(player):
    return (int(player['race']) in (2, 5, 6, 8, 10))

# Get string name of race index
def getRace(race):
    races = {1: 'Human',
             2: 'Orc',
             3: 'Dwarf',
             4: 'Night Elf',
             5: 'Undead',
             6: 'Tauren',
             7: 'Gnome',
             8: 'Troll',
             10: 'Blood Elf',
             11: 'Draenei'}
    if (race in races.keys()):
        return races[race]
    else:
        return "RaceErr"

# Get string name of class index
def getClass(cl):
    classes = {1: 'Warrior',
               2: 'Paladin',
               3: 'Hunter',
               4: 'Rogue',
               5: 'Priest',
               7: 'Shaman',
               8: 'Mage',
               9: 'Warlock',
               11: 'Druid'}
    if (cl in classes.keys()):
        return classes[cl]
    else:
        return "ClassErr"

# Generate the proper HTML for the zone <div>
def generateHTML(me, players, zone):
	actualPlayers = [p for p in players if p['zone'] != u'Unknown' and p['name'] != u'Dead']
	if zone is None: zone = "map"
	else: zone = str(re.sub(r'\W', '', zone))
	outHTML = "##" + zone + "##\n"
	for p in actualPlayers:
		try:
			# translate the "POMM" coords to the zone
			pCoords = Point(int(p['x']), int(p['y']))
			if zone is not 'map': pCoords = WebMapCoordsToZoneCoords2(zone, pCoords.x, pCoords.y)
			pName = p['name']
			pRace = int(p['race'])
			pRaceStr = getRace(pRace)
			pGender = int(p['gender'])
			pClass = int(p['cl'])
			pClassStr = getClass(pClass)
			pLevel = p['level']
			# make the right point graphic and popup header style
			if ((me is not None) and (pName == me)):
				pStyle = "self"
			elif (isHorde(p)):
				pStyle = "h"
			else:
				pStyle = "a"
			outHTML += POINT_HTML % (pStyle, pCoords.x, pCoords.y, pStyle, pName, pRace, pGender, pClass, pRaceStr, pClassStr, pLevel, pName)
		except Exception, e:
			print e, outHTML, "<h2>zone = '", zone, "'</h2>"
	return outHTML.encode(CHARSET)

# Determine the "filter" zone from the parameters
def getZoneFromPlayer(char, players):
	for p in players:
		if (p['name'] == char):
			return p['zone']
	return None

# Main function!
def main():
    print "Content-Type: text/html; charset=" + CHARSET + "\n\n"
    # get either player name or zone
    parameters = parseQueryString()
    char, zone = parameters['char'], parameters['zone']
    players = parsePlayerData()
    players = filter(lambda p: p['zone'] != u'Unknown' and p['name'] != u'Dead', players)
    if char is not None:
        char = char.decode('latin1')
        zone = getZoneFromPlayer(char, players)
    if zone is not None:
        players = filter(lambda p: p['zone'] == zone, players)
    print generateHTML(char, players, zone)
    conn.close()

main()
