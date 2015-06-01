d4 = ("d4", "72fdca01-ff61-4dd2-a6b8-43f567f90ff7")
redDie = ("redDie", "1f1a643b-2aea-48b2-91c8-96f0dffaad48")
blueDie = ("blueDie", "XXXXXX")
greenDie = ("greenDie", "XXXXX")
purpleDie = ("purpleDie", "XXXXX")
d8 = ("d8", "4165d32c-7b07-4040-8e57-860a95a0dc69")
d10 = ("d10", "3b7cbb3a-4f52-4445-a4a5-65d5dfd9fa23")
d12 = ("d12", "53d1f6b4-03f6-4b8b-8065-d0759309e00d")
plus = ("+", "1b08a785-f745-4c93-b0f1-cdd64c89d95d")
minus = ("-", "b442c012-023f-42d1-9d28-e85168a4401a")
timer = ("Timer", "d59b44ba-cddf-49f9-88f5-1176a305f3d3")

BoardWidth = 850
BoardHeight = 300
StoryY = -BoardHeight/2
LocationY = StoryY + 190

showDebug = False #Can be changed to turn on debug

#------------------------------------------------------------
# Utility functions
#------------------------------------------------------------

def debug(str):
	if showDebug:
		whisper(str)
		
def toggleDebug(group, x=0, y=0):
	global showDebug
	showDebug = not showDebug
	if showDebug:
		notify("{} turns on debug".format(me))
	else:
		notify("{} turns off debug".format(me))

def cardFunctionName(card): # Removes special characters from the card name giving a string we can use as a function name
	if card.Name[0].isdigit():
		cardName = "S{}".format(card.Name)
	else:
		cardName = card.Name
	return cardName.replace(' ','').replace('!','').replace("'","").replace('?','').replace('-','')
	
def shuffle(pile, synchronise=False):
	mute()
	if pile is None or len(pile) == 0: return
	pile.shuffle()
	if synchronise:
		sync()
	notify("{} shuffles '{}'".format(me, pile.name))
	
#Return the default x coordinate of the players hero
#We Leave space for 4 piles (Chapter, Mission, Master, Minion, Omen) then place the characters
def PlayerX(player):
	room = int(BoardWidth / (len(getPlayers()) + 5))
	return  room*(player+5) - room/2 - 32 - BoardWidth/2

def LocationX(i, nl):
	room = int(BoardWidth / nl)
	return room*i - room/2 - 32 - BoardWidth/2
	
def numLocations(): #2 more locations than players but modified by the extra locations counter in the shared tab
	n = len(getPlayers())+2+shared.ExtraLocations
	if n < 1:
		return 1
	if n > 8:
		return 8
	return n
	
def num(s):
   if not s: return 0
   try:
      return int(s)
   except ValueError:
      return 0

def eliminated(p, setVal=None):
	val = list(getGlobalVariable("Eliminated"))	
	if setVal is None:
		return val[p._id] == '1'
	if setVal == True:
		val[p._id] = '1'
	else:
		val[p._id] = '0'
	setGlobalVariable("Eliminated", "".join(val))
	return setVal
	
#Check to see if a card at x1,y1 overlaps a card at x2,y2
#Both have size w, h	
def overlaps(x1, y1, x2, y2, w, h):
	#Four checks, one for each corner
	if x1 >= x2 and x1 <= x2 + w and y1 >= y2 and y1 <= y2 + h: return True
	if x1 + w >= x2 and x1 <= x2 and y1 >= y2 and y1 <= y2 + h: return True
	if x1 >= x2 and x1 <= x2 + w and y1 + h >= y2 and y1 <= y2: return True
	if x1 + w >= x2 and x1 <= x2 and y1 + h >= y2 and y1 <= y2: return True
	return False
	
def cardHere(x, y, checkOverlap=True, cards=table):
	cw = 0
	ch = 0
	for c in cards:
		cx, cy = c.position
		if checkOverlap:
			cw = c.width()
			ch = c.height()
		if overlaps(x, y, cx, cy, cw, ch):
			return c
	return None

def cardX(card):
	x, y = card.position
	return x
	
def cardY(card):
	x, y = card.position
	return y

def clearTargets(group=table, x=0, y=0):
	for c in group:
		if c.controller == me or (c.targetedBy is not None and c.targetedBy == me):
			c.target(False)

def findCard(group, model):
	for c in group:
		if c.model == model:
			return c
	return None

#Work out which of the shared piles a card comes from based on its type/subtype
def comesFrom(card):
	if card is None:
		return None
	if card.Type is not None:
		if card.Type in shared.piles:
			return shared.piles[card.Type]
	if card.Subtype is not None and card.Subtype in shared.piles:
		return shared.piles[card.Subtype]
	return None
	
def returnToBox(card):
	locked = False
	if card.Type == '?': # Not visible
		locked = lockPile(shared.piles['Internal'])
		if not locked: return
		group = card.group
		if group == table:
			x, y = card.position
		card.moveTo(shared.piles['Internal']) # Ensures the card properties are visible
	
	dest = comesFrom(card)		
	if dest is None: # Don't know where to put it
		notify("{} Fails to find place for '{}' in the box".format(me, card))
		if locked: # We moved it, so return it to where it started
			if group == table:
				card.moveToTable(x, y)
			else:
				card.moveTo(group)
	else: # Move to the correct pile - aiming to keep in alphabetical order
		card.link(None)
		index = 0
		for c in dest:
			if c.Name >= card.Name:
				break
			index += 1
		if dest.controller != me:
			card.setController(dest.controller) #Pass control to the pile controller and ask them to move it
			remoteCall(dest.controller, "moveCard", [card, dest, index])
		else:
			card.moveTo(dest, index)
	
	if locked:
		unlockPile(shared.piles['Internal'])

# Called remotely to move a card to a pile we control
def moveCard(card, pile, index):
	mute()
	card.moveTo(pile, index)
	
def isOpen(card):
	if card is None or card.Type != 'Location':
		return False
	return (card.orientation == Rot0 and card.alternate != "B")
	
def isNotPermanentlyClosed(card):
	if card is None or card.Type != 'Location':
		return False
	if card.Name in ('Abyssal Rift'):
		return True
	return card.alternate != "B"
	
#Any card loaded into the player area must be removed from the box otherwise we end up with duplicates
#Get the card controller to find and then delete the card
def inUse(pile):
	mute()
	for card in pile:
		if card.Subtype in shared.piles:
			if shared.piles[card.Subtype].controller != me:
				remoteCall(shared.piles[card.Subtype].controller, "findAndDelete", [me, card])
			else:
				findAndDelete(me, card)

#Find an exact match based on the card model, if none look for a name match
def findAndDelete(who, card):
	mute()
	found = findCard(shared.piles[card.Subtype], card.model)
	if found is None:
		found = findCardByName(shared.piles[card.Subtype], card.Name)
	if found is not None:
		found.delete()
	else:
		notify("{} is using '{}' which is not in the box".format(who, card))

def rollDice(card): #Roll the dice based on the number of tokens
	mute()
	rolled = 0
	dice = ""
	detail = ""
	for die in [ d12, d10, d8, redDie, blueDie, greenDie, purpleDie, d4 ]:
		count = card.markers[die]
		if count > 0:
			dice += " + {}{}".format(count, die[0])
			detail += " + ["
			while count > 0:
				roll = 1 + int(random() * num(die[0][1:]))
				detail ="{}{}{}".format(detail,roll,"+" if count > 1 else "]")
				rolled += roll
				count -= 1
			card.markers[die] = 0
	
	if card.markers[plus] > 0:
		rolled += card.markers[plus]
		dice = "{} + {}".format(dice, card.markers[plus])
		detail = "{} + {}".format(detail, card.markers[plus])
		card.markers[plus] = 0
	if card.markers[minus] > 0:
		rolled -= card.markers[minus]
		dice = "{} - {}".format(dice, card.markers[minus])
		detail = "{} - {}".format(detail, card.markers[minus])
		card.markers[minus] = 0
	
	if len(dice) > 0:
		playSound("dice")
		notify("{} rolls {} on {}".format(me, dice[3:], card))
		notify("{} = {}".format(detail[3:], rolled))
		return True
	
	return False

def findCardByName(group, name):
	debug("Looking for '{}' in '{}'".format(name, group.name))
	for card in group:
		if card.Name == name:
			return card
	return None
		
def d12Add(card, x=0, y=0):
	addToken(card, d12)

def d12Sub(card, x=0, y=0):
	subToken(card, d12)
	
def d10Add(card, x=0, y=0):
	addToken(card, d10)

def d10Sub(card, x=0, y=0):
	subToken(card, d10)	
	
def d8Add(card, x=0, y=0):
	addToken(card, d8)

def d8Sub(card, x=0, y=0):
	subToken(card, d8)	
	
def redDieAdd(card, x=0, y=0):
	addToken(card, redDie)

def redDieSub(card, x=0, y=0):
	subToken(card, redDie)	
	
def blueDieAdd(card, x=0, y=0):
	addToken(card, blueDie)

def redDieSub(card, x=0, y=0):
	subToken(card, blueDie)	
	
def greenDieAdd(card, x=0, y=0):
	addToken(card, greenDie)

def greenDieSub(card, x=0, y=0):
	subToken(card, greenDie)	
	
def purpleDieAdd(card, x=0, y=0):
	addToken(card, purpleDie)

def purpleDieSub(card, x=0, y=0):
	subToken(card, purpleDie)	
	
def d4Add(card, x=0, y=0):
	addToken(card, d4)

def d4Sub(card, x=0, y=0):
	subToken(card, d4)	
		
def plusThree(card, x=0, y=0):
	tokens(card, 3)

def plusTwo(card, x=0, y=0):
	tokens(card, 2)
	
def plusOne(card, x=0, y=0):
	tokens(card, 1)	
	
def minusThree(card, x=0, y=0):
	tokens(card, -3)

def minusTwo(card, x=0, y=0):
	tokens(card, -2)

def minusOne(card, x=0, y=0):
	tokens(card, -1)

# Find the top pile under this card
def overPile(card, onlyNexus=False):
	debug("Checking to see if '{}' is over a pile".format(card))	
	piles = sorted([ c for c in table if c.pile() is not None and (c.Type == 'Nexus' or not onlyNexus) ], key=lambda c: -c.getIndex)
	x, y = card.position
	return cardHere(x, y, True, piles)
	
def closeNexus(card, perm):
	mute()
	if card.Type != 'Nexus':
		notify("This is not a nexus ...")
		return False
	
	if perm == False:
		card.orientation = Rot90
		notify("{} temporarily closes '{}'".format(me, card))
		return True
		
	# Move cards from location pile back to box
	# If we find the Master then the location is not closed and the Master is displayed
	# We need to use a pile with full visibility to access the card type
	pile = card.pile()
	visible = shared.piles['Internal']
	if not lockPile(visible): return
	
	debug("Cleaning up pile '{}'".format(pile.name))
	for c in pile:
		c.moveTo(visible)
	
	master = [ c for c in visible if c.Subtype == 'Master' ]
	for c in master:
		notify("You find {} while attempting to close this nexus".format(c))
		c.moveTo(pile)
		
	for c in visible: #Banish the remaining cards
		debug("Unexplored ... '{}'".format(c))
		banishCard(c)
	
	unlockPile(visible)
				
	if len(pile) > 1:
		shuffle(pile)
	
	if len(master) > 0: # Close fails - we temporarily close it instead
		card.orientation = Rot90 
		return False
	
	notify("{} permanently closes '{}'".format(me, card))
	if len(card.Attr4) > 0 and card.Attr4 != "No effect.":
		notify(card.Attr4)
	flipCard(card)
	return True
	
def cleanupGame(cleanupStory=False):
	for p in getPlayers():
		if p == me:
			cleanupPiles(cleanupStory)
		else:
			remoteCall(p, "cleanupPiles", [cleanupStory])

def cleanupPiles(cleanupStory=False): #Clean up the cards that we control
	for card in table:
		if card.controller == me:
			if card.Type == 'Character':
				if card.Subtype == 'Token':
					card.moveTo(card.owner.hand)
				else:
					card.switchTo() # Display side A of the card as it shows the deck makeup
			elif not cleanupStory and card.Type == 'Gift': # Return displayed cards to the controller's hand
				card.moveTo(me.hand)
			elif cleanupStory or card.Type != 'Story':
				returnToBox(card)

	for i in range(8): # Loop through 8 location decks
		pile = shared.piles["Nexus{}".format(i+1)]
		if pile.controller == me:
			for card in pile:
				returnToBox(card)

	for p in [ 'Omen Deck', 'Special', 'Mission' ]:
		pile = shared.piles[p]
		if pile.controller == me:
			for card in pile:
				returnToBox(card)
	
#------------------------------------------------------------
# Global variable manipulations function
#------------------------------------------------------------	

# A Global variable is created for each location pile named after the location
# No functional interface is supplied for this however personal globals needed for reconnect are

def storeHandSize(h):
	me.setGlobalVariable('HandSize', str(h))

def getHandSize(p=me):
	return num(p.getGlobalVariable('HandSize'))
	
def storeFavoured(f):
	me.setGlobalVariable('Favoured', str(f))

def getFavoured():
	return eval(me.getGlobalVariable('Favoured'))
	
def storeCards(s):
	me.setGlobalVariable('Cards', s)
	
def getCards():
	return me.getGlobalVariable('Cards')

def lockInfo(pile):
	if pile is None: return (None, 0)
	lock = getGlobalVariable(pile.name)
	if len(lock) == 0:
		return (None, 0)
	info = lock.split()
	return (info[0], num(info[1]))
	
def lockPile(pile):
	mute()
	if pile is None: return False
	# Attempt to lock the shared pile
	# Write the player name and count into a global named after the pile
	who, count = lockInfo(pile)
	if who != None and who != me.name:
		whisper("{} has temporarily locked the game - please try again".format(who))
		return False
		
	if pile.controller != me:
		pile.setController(me)
		sync()
	setGlobalVariable(pile.name, "{} {}".format(me.name, count+1))
	return True

def unlockPile(pile):
	mute()
	if pile is None: return False
	who, count = lockInfo(pile)
	if who is None:
		debug("{} tries to unlock pile '{}' - not locked".format(me, pile.name))
		return False
	if who != me.name:
		debug("{} tries to unlock pile '{}' - locked by {}".format(me, pile.name, info[0]))
		return False
	if count <= 1:
		setGlobalVariable(pile.name, None)
	else:
		setGlobalVariable(pile.name, "{} {}".format(me.name, count-1))
	return True

#Look at the global variables to determine who was the active player on the given turn
def getPlayer(turn):
	for var in [ 'Current Turn', 'Previous Turn' ]:
		info = getGlobalVariable(var)
		if len(info) > 0:
			t, p = info.split('.')
			if int(t) == turn:
				for player in getPlayers():
					if player.name == p:
						return player
	return None
	
#---------------------------------------------------------------------------
# Call outs
#---------------------------------------------------------------------------

def setGlobals():
	mute()
	setGlobalVariable('Fleet', '[]') #CHANGE
	
def deckLoaded(player, groups):
	mute()

	if player != me:
		return
		
	isShared = False
	for p in groups:
		if p.name in shared.piles:
			isShared = True
		
	if not isShared: # Player deck loaded
		playerSetup()
	
def startOfTurn(player, turn):
	mute()
	debug("Start of Turn {} for player {}".format(turn, player))
	
	clearTargets()
	if player == me: # Store my details in the global variable
		setGlobalVariable("Previous Turn", getGlobalVariable("Current Turn"))
		setGlobalVariable("Current Turn", "{}.{}".format(turn, player.name))
			
	lastPlayer = getPlayer(turn-1)
	debug("Last Player = {}, player = {}, me = {}".format(lastPlayer, player, me))
	if lastPlayer is not None and me == lastPlayer:
		drawUp(me.hand)
		
	# Pass control of the shared piles and table cards to the new player
	debug("Processing table ...")
	for card in table: 
		if card.controller == me: # We can only update cards we control	
			if card.orientation != Rot0: #Re-open any temporarily closed locations
				card.orientation = Rot0	
			if card.Type == 'Character':
				if card.owner == me: #Highlight my avatar
					if player == me: # I am the active player
						card.sendToFront()
						card.highlight = "#82FA58" # Green
					elif eliminated(me):
						card.highlight = "#FF0000" # Red
					else:
						card.highlight = None
			elif player != me: #Pass control of all non-character cards to the new active player
				card.setController(player)
	
	debug("Processing shared piles ...")	
	for name in shared.piles:
		if shared.piles[name].controller == me and player != me: # Hand over control to the new player
			shared.piles[name].setController(player)
		
	if player == me:
		sync() # wait for control of cards to be passed to us
		# Perform scenario specific actions
		scenario = findScenario(table)
		if scenario is not None:
			fn = cardFunctionName(scenario)
			if fn in globals():
				globals()[fn]('StartOfTurn')
		advanceOmenDeck()	
		
def checkMovement(player, card, fromGroup, toGroup, oldIndex, index, oldX, oldY, x, y, isScriptMove, highlight=None, markers=None):
	checkMovementAll(player, card, fromGroup, toGroup, oldIndex, index, oldX, oldY, x, y, False, highlight, markers)
	
def checkScriptMovement(player, card, fromGroup, toGroup, oldIndex, index, oldX, oldY, x, y, isScriptMove, highlight=None, markers=None):
	checkMovementAll(player, card, fromGroup, toGroup, oldIndex, index, oldX, oldY, x, y, True, highlight, markers)
		
#
#Card Move Event
# Enforce game logic for avatars and omen deck
#
def checkMovementAll(player, card, fromGroup, toGroup, oldIndex, index, oldX, oldY, x, y, isScriptMove, highlight, markers, faceup=None):
	mute()
	bd = shared.piles['Blessing Discard']
	if fromGroup == bd or toGroup == bd or me.isActivePlayer: #Check to see if the current blessing card needs to change
		bx = PlayerX(0)
		by = StoryY	
		bc = None #Temp blessing card	
		for c in table:
			if c.pile() == shared.piles['Blessing Deck']:
				bx, by = c.position
				if fromGroup == bd or toGroup == bd: # Tidy up the temp blessing card
					if c.controller == me:
						c.link(None)
						c.delete()
				else:
					bc = c
				break
					
		if me.isActivePlayer and len(bd) > 0 and bc is None: # Create a copy of the top card
			bc = table.create(bd.top().model, bx, by)
			bc.link(shared.piles['Blessing Deck'])
	
	if player != me or isScriptMove or card.Type != 'Character' or card.Subtype != 'Token': # Nothing to do
		return	

	# Our Avatar has moved
	if fromGroup == table and toGroup != table: # Did we move the avatar off the table
		# Don't allow this
		card.moveToTable(oldX, oldY)
		return
	if fromGroup != table and toGroup == table: # Did we move the avatar onto the table
		# If the scenario hasn't been set up yet return the avatar to hand and issue a warning
		locs = [ c for c in table if c.Type == 'Location' ]
		if len(locs) == 0:
			whisper("Ensure the scenario is set up before placing {} at your starting location".format(card))
			card.moveTo(fromGroup)
			return
		playerReady(card)
		
def playerReady(card):
	mute()
	#Ensure side B of the character card is face up
	for c in table:
		if c.owner == me and c.Type == 'Character' and c != card:
			c.switchTo('B')

	debug("{} is ready".format(me))
	#Move all player card (Gifts) to Discarded pile - then shuffle ready for dealing
	for pile in [ me.hand, me.Buried, me.deck ]:
		for c in pile:
			if c.Type == 'Character':
				c.moveTo(me.hand)
			elif c.Type == 'Feat':
				c.moveTo(me.Buried)
			else:
				c.moveTo(me.Discarded)
	shuffle(me.Discarded, True)
	size = len(me.Discarded)
	choices = getFavoured()					
	if 'Your choice' in choices: # Ignore the stored value and make a list of the card types in the deck
		choices = []
		for card in me.Discarded:	
			if card.Subtype not in choices:
				choices.append(card.Subtype)
			if card.Subtype == 'Loot': # Loots have a secondary type too
				if card.Subtype2 not in choices:
					choices.append(card.Subtype2)
		
	#Prompt user to select favoured card type
	choice = None
	if len(choices) > 1:
		while choice == None or choice == 0:
			choice = askChoice("Favoured Card Type", choices)
		favoured = choices[choice-1]
	elif len(choices) == 1:
		favoured = choices[0]
	else:
		favoured = None
	handSize = getHandSize()
	ci = 0
	if favoured is not None: # If a favoured card type is defined skip cards until we reach one
		for card in me.Discarded:
			if card.Subtype == favoured or (card.Subtype == 'Loot' and card.Subtype2 == favoured): break
			ci += 1
		
	if ci >= size:
		ci = 0
		notify("{} has an invalid deck - no favoured cards ({})".format(me, favoured))
	
	if ci > 0: #Move the top cards to deck so that the favoured card is at the top of the Discarded pile
		for card in me.Discarded.top(ci):
			card.moveToBottom(me.Discarded)

	for c in me.Discarded.top(handSize):
		c.moveTo(me.hand)
	#Move the rest of the cards into the deck
	for card in me.Discarded:
		card.moveTo(me.deck)
	
	sync()
	#The first player to drag to the table becomes the active player
	tokens = [ c for c in table if c.Subtype == 'Token' ]
	if len(tokens) == 1:
		#Check to see who the active player is
		active = None
		for p in getPlayers():
			if p.isActivePlayer:
				active = p
				break
		if active is None: # At the start of a game no one is active but anyone can set the active player
			makeActive(me)
		else:
			remoteCall(active, "makeActive", [me])

def makeActive(who):
	mute()
	if who != me:
		debug("{} passes control to {}".format(me, who))
	who.setActivePlayer()

# Called when a player draws an arrow between two cards (or clears an arrow)
# If the source card has dice on it, they are moved to the destination
# This is done in two parts, the controller of the dst card adds dice based on the src
# Then the controller of the src card removes the dice on it
def passDice(player, src, dst, targeted):
	mute()
	if targeted and dst.controller == me:	
		whisper("dst controller is {}".format(dst.controller))
		dice=""
		for m in [ d12, d10, d8, d6, d4 ]:
			if src.markers[m] > 0:
				dice = "{} + {}{}".format(dice, src.markers[m], m[0])
				dst.markers[m] += src.markers[m]
		if src.markers[plus] > 0:
			dice = "{} + {}".format(dice, src.markers[plus])
			dst.markers[plus] += src.markers[plus]
		if src.markers[minus] > 0:
			dice = "{} - {}".format(dice, src.markers[minus])
			dst.markers[minus] += src.markers[minus]
		if src.controller != me:
			remoteCall(src.controller, "clearDice", [src])
		else:
			clearDice(src)
		notify("{} Moves {} from {} to {}".format(player, dice[3:], src, dst))

# Remove all dice from the card
def clearDice(card):
	mute()
	whisper("Clearing dice on {}".format(card))
	for m in [ d12, d10, d8, d6, d4, plus, minus ]:
		if card.markers[m] > 0:
			card.markers[m] = 0	
		
#---------------------------------------------------------------------------
# Table group actions
#---------------------------------------------------------------------------
		
# Remove targeting arrows after a check
def clearTargets(group=table, x=0, y=0):
	for c in group:
		if c.controller == me or (c.targetedBy is not None and c.targetedBy == me):
			c.target(False)
			
#Table action - prompts the player to pick an adventure path, an adventure and a scenario
#If there is already a scenario on the table clear it away
def pickMission(group=table, x=0, y=0):
	mute()
	
	#If any of the players haven't loaded their deck we abort
	for p in getPlayers():
		if getHandSize(p) == 0:
			whisper("Please wait until {} has loaded their deck and then try again".format(p))
			return
	
	#Take control of the shared piles
	for name in shared.piles:
		if shared.piles[name].controller != me:
			shared.piles[name].setController(me)
	sync()
	
	story = [ card for card in group if card.Type == 'Story' ]
	if len(story) > 0:
		if not confirm("Clear the current game?"):
			return
		cleanupGame(True)
		sync() #wait for other players to tidy up their cards
	
	setGlobalVariable('Previous Turn', '')
	setGlobalVariable('Current Turn', '')
	setGlobalVariable('Remove Basic', '')
	setGlobalVariable('Remove Elite', '')
	
	#Pick the new Mission
	chapters = [ card.Name for card in shared.piles['Story'] if card.Subtype == 'Chapter' ]

	if len(chapters) < 2:
		choice = len(chapters)
	else:
		choice = askChoice("Choose Chapter", chapters)
	if choice <= 0 or chapters[choice-1] == 'None': # Not using a chapter card
		missions = [ card.Name for card in shared.piles['Story'] if card.Subtype == 'Mission' ]
	else:
		chapter = findCardByName(shared.piles['Story'], chapters[choice-1])
		chapter.moveToTable(PlayerX(-3), StoryY)
		flipCard(chapter)
		loaded = [ card.Name for card in shared.piles['Story'] if card.Subtype == 'Mission' ]
		missions = []
		for o in chapter.Attr1.splitlines(): # Build up a list of options that have been loaded and in the order given
			if o in loaded:
				missions.append(o)
	if len(missions) < 2:
		choice = len(missions)
	else:
		choice = askChoice("Choose Mission", missions)
	if choice > 0:
		mission = findCardByName(shared.piles['Story'], missions[choice-1])
		mission.moveToTable(PlayerX(-2),StoryY)


def nextTurn(group=table, x=0, y=0):
	mute()
	# Only the current active player can do this
	if not me.isActivePlayer:
		whisper("Only the active player may perform this operation")
		return
	players = getPlayers()
	nextID = (me._id % len(players)) + 1
	while nextID <> me._id:
		for p in players:
			if p._id == nextID and not eliminated(p):
				p.setActivePlayer()
				return
		nextID = (nextID % len(players)) + 1
	me.setActivePlayer()
	
def randomHiddenCard(group=table, x=0, y=0):
	pile, trait = cardTypePile()
	if pile is None: return
	if pile.controller != me:
		remoteCall(pile.controller, "randomCardN", [me, pile, trait, x, y, 1, True])
	else:
		randomCardN(me, pile, trait, x, y, 1, True)
	
def randomCard(group=table, x=0, y=0):
	pile, trait = cardTypePile()
	if pile is None: return
	if pile.controller != me:
		remoteCall(pile.controller, "randomCardN", [me, pile, trait, x, y, 1])
	else:
		randomCardN(me, pile, trait, x, y, 1)

def randomCards(group=table, x=0, y=0):
	quantity = [ "One", "Two", "Three", "Four", "Five", "Six" ]
	choice = askChoice("How many?", quantity)
	if choice <= 0:
		return
	isHidden = askChoice("Hide cards?",["Yes", "No"])
	pile, trait = cardTypePile()
	if pile is None: return
	if pile.controller != me:
		if isHidden == 1:
			remoteCall(pile.controller, "randomCardN", [me, pile, trait, x, y, choice, True])
		else:
			remoteCall(pile.controller, "randomCardN", [me, pile, trait, x, y, choice])
	else:
		if isHidden == 1:
			randomCardN(me, pile, trait, x, y, choice, True)
		else: 
			randomCardN(me, pile, trait, x, y, choice)

def hasTrait(card, trait):
	if card is None:
		return False
	if trait == "Any":
		return True
	if card.Traits is None or len(card.Traits) == 0:
		return False
	return trait in card.Traits.splitlines()
	
def randomCardN(who, pile, trait, x, y, n, hide=False):
	mute()
	if y > 0:
		y -= 50
	cards = [ c for c in pile if hasTrait(c, trait) ]
	while n > 0 and len(cards) > 0:
		card = cards[int(random()*len(cards))]
		cards.remove(card)
		card.moveToTable(x, y, hide)
		if who != me:
			card.setController(who)
		x = x + 10
		n -= 1	

def cardTypePile(): #START HERE JUNE 1
	mute()
	types = ["Henchman", "Monster", "Barrier", "Armor", "Weapon", "Spell", "Item", "Ally", "Blessing", "Ship"]
	choice = askChoice("Pick card type", types)
	if choice <= 0:
		return None, None	
	pile = shared.piles[types[choice-1]]
	
	# Ask for an optional trait
	traits = [ ]	
	for c in pile:
		for t in c.Traits.splitlines():
			if t != "and" and t not in traits:
				traits.append(t)
	traits.sort()
	traits.insert(0, "Any")
	choice = 1
	if len(traits) > 1:
		choice = askChoice("Pick a trait", traits)
		if choice <= 0:
			choice = 1
	return pile, traits[choice-1]
	
#---------------------------------------------------------------------------
# Menu items - called to see if a menu item should be shown
#---------------------------------------------------------------------------
def isPile(cards):
	for c in cards:
		if c.pile() is None:
			return False
	return True

def isLocation(cards):
	for c in cards:
		if c.Type != 'Location':
			return False
	return True

def isVillain(cards):
	for c in cards:
		if c.Subtype != 'Villain':
			return False
	return True

def isShip(cards):
	for c in cards:
		if c.Type != 'Ship':
			return False
	return True

def isEnemyShip(cards):
	for c in cards:
		if c.type != 'Ship' or c.pile() == shared.piles['Plunder']:
			return False
	return True

def isWrecked(cards):
	for c in cards:
		if c.Type != 'Ship' or c.alternate != "B":
			return False
	return True
	
def isNotWrecked(cards):
	for c in cards:
		if c.Type != 'Ship' or c.alternate == "B":
			return False
	return True

def hasPlunder(cards):
	for c in cards:
		if c.Type != 'Ship' or c.pile() is None or len(c.pile()) == 0:
			return False
	return True

def isBoon(cards):
	for c in cards:
		if c.Type != 'Boon':
			return False
	return True
	
def isBoxed(cards):
	for c in cards:
		if c.Type not in ('Boon', 'Bane', 'Feat', 'Ship'):
			return False
	return True
	
def hasDice(cards):
	for c in cards:
		count = 0
		for die in [ d12, d10, d8, d6, d4 ]:
			count += c.markers[die]
		if count == 0:
			return False
	return True

def usePlunder(groups):
	#Check to see if the group contains a ship
	for g in groups:
		for c in g:
			if c.Type == 'Ship':
				return True
	return False