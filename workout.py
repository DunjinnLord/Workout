import board
import digitalio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306
import paho.mqtt.client as mqtt
from time import sleep
from gpiozero import Button
from rpi_TM1638 import TMBoards


# Updates the numbers on the LED/key display
def num_update():
	TM.segments[0] = '{:04d}'.format(abs(num_left)%10000)
	TM.segments[4] = '{:04d}'.format(abs(num_right)%10000)
	return


# Function for the workout button
# Publishes "Workout?" to the f20v topic
# Resets the count variable if it is higher than 2
# Whoever presses the workout button becomes Player1
def press():
	global count
	global player

	# Sets the player who pressed the workout button to be player1
	player = "f20v/Player1"
	if (count > 2):
		count = 0
	sleep(0.2)
	client.publish("f20v", "Workout?", qos = 0, retain = False)


# Function for the Yes button
# Does the same as the press function excepts it publishes "Yes" to the topic
def accept():
	global count
	global player
	sleep(0.2)

	# The player who presses the Yes button becomes player 2
	# This also resets player to player 2 in case the player was player 1 the previous workout
	player = "f20v/Player2"
	if (count > 2):
		count = 0
	client.publish("f20v", "Yes", qos = 0, retain = False)


# Function for the no button
def decline():
	client.publish("f20v", "No", qos = 0, retain = False)


# Subscribes to 5 different topics
def on_connect(client, userdata, flags, rc):
	client.subscribe([("f20v", 0), ("f20v/Player1", 0), ("f20v/Player2", 0)])



# Publishes the number of reps to do for the given workout
def show_reps():
	client.publish("f20v", workouts[key], qos = 0, retain = False)



# This function reacts to certain messages published to certain topics
def on_message(client, userdata, msg):
	global result
	global count
	global player
	global num_right

	# Player 2 gets Player1's results and the get_result function determines the winner and publishes it on this topic
	if (msg.topic == "f20v/Player1"):
		if (player == "f20v/Player2"):
			result = int(msg.payload)
			get_result(result, num_right)

		else:  # If you are player 1 then print what is published on this topic to the oled
			print_to_oled(msg)

	# Player1 gets Player 2's results and the get_result function determines the winner and publishes it on this topic
	if (msg.topic == "f20v/Player2"):
		if (player == "f20v/Player1"):
			result = int(msg.payload)
			get_result(result, num_right)

		else:  # If you are player 2 then print what is published on this topic to the oled
			print_to_oled(msg)


	if (msg.topic == "f20v"):

		# When the number of reps to do is published in f20v, print it to the oled
		# and start the train function
		if (msg.payload.decode("utf-8") in workouts):
			print_to_oled(msg)
			train()
		print_to_oled(msg)

		if ("Yes" in str(msg.payload)):
			count += 1
			if (count == 2):  # This makes the oled show the number of reps for the given workout
				if (player == "f20v/Player1"):  # Player 1 publishes the number of reps to do
					client.publish("f20v", workouts[workout], qos = 0, retain = False)
					print_to_oled()

			# When a workout has been selected and accepted call the train function
			if (player == "f20v/Player1" and count == 1):
				select_workout(client, userdata)

		if ("No" in str(msg.payload)):
			if (count == 1 and player == "f20v/Player1"):  # If the no button is pushed in response to a suggested workout, the select_workout will be called again to select another workout
				select_workout(client, userdata)
			else:
				player = "Player2"  # Resets player to player 2 in case they don't want to work out


# Gets each players results from the workout and publishes them to their own topic
# Determines the winner
# Count variable is set to 3 so the published messages will be scrolled on the oled display
def get_result(their_score, my_score):
	global message
	global count
	global player
	count = 3

	message = "Opponent got "
	message += str(their_score)
	message += " sets"
	client.publish(player, message, qos = 0, retain = False)

	message = "You got "
	message += str(my_score)
	message += " sets"
	client.publish(player, message, qos = 0, retain = False)


	# Compares the results from player 1 and player 2 and determines the winnder
	# The result is then published to f20v/Player1 if you are player 1 or f20v/Player2 if you are player 2
	if (my_score > their_score):
		client.publish(player, "YOU WIN", qos = 0, retain = False)

	elif (my_score == their_score):
		client.publish(player, "DRAW", qos = 0, retain = False)

	else:
		client.publish(player, "YOU LOSE", qos = 0, retain = False)



# This function counts the sets done when button 8 is pushed
# The set count is shown on the right side of the diplay
# When button 1 is pushed the screen turns off and the function is exited
def train():
	global num_left
	global num_right

	num_left = 0000
	num_right = 0000
	TM.turnOn(2)

	while True:
		for i in range(8):
			TM.leds[i] = True if TM.switches[i] else False
		if TM.switches[0]:  # This button is pushed when the workout is done
			TM.turnOff()
			break
		if TM.switches[1]: num_right = 0000
		if TM.switches[7]: num_right += 1  # Counts the number of sets done
		sleep(0.3)  # Short delay so the set count is not incremented too quickly when the button is pushed
		num_update()
	client.publish(player, num_right, qos = 0, retain = False)  # Publishes the results in the given player's topic


# Use the buttons on the LED&KEY display to select a workout
# Only player 1 can do this
def select_workout(client, userdata):
	global num_left
	global num_right
	global workout
	global workout_list
	global key

	workout = -1
	num_left = 1234
	num_right = 5678
	TM.turnOn(2)

	# The variable "workout" becomes equal to the button pushed on the LED&KEY display
	# It is then used to get a workout from a list with an index equal to the value the variable "workout" holds
	while True:
		for i in range(8):
			TM.leds[i] = True if TM.switches[i] else False
		if TM.switches[0]:
			workout = 0
			key = workout_list[workout]
			break
		if TM.switches[1]:
			workout = 1
			key = workout_list[workout]
			break
		if TM.switches[2]:
			workout = 2
			key = workout_list[workout]
			break
		if TM.switches[3]:
			workout = 3
			key = workout_list[workout]
			break
		if TM.switches[4]:
			workout = 4
			key = workout_list[workout]
			break
		if TM.switches[5]:
			workout = 5
			key = workout_list[workout]
			break
		if TM.switches[6]:
			workout = 6
			key = workout_list[workout]
			break
		if TM.switches[7]:
			workout = 7
			key = workout_list[workout]
			break
		num_update()
	client.publish("f20v", workout_list[workout], qos = 0, retain = False)  # The content of the list at the given index is published to f20v



def print_to_oled(msg):
	global message

	oled_reset = digitalio.DigitalInOut(board.D4)

	# Change these
	# to the right size for your display!
	WIDTH = 128
	HEIGHT = 32  # Change to 64 if needed
	BORDER = 0

	# Use for I2C.
	#i2c = board.I2C()
	#oled = adafruit_ssd1306.SSD1306_I2C(WIDTH, HEIGHT, i2c, addr=0x3C, reset=oled_reset)

	# Use for SPI
	spi = board.SPI()
	oled_cs = digitalio.DigitalInOut(board.D5)
	oled_dc = digitalio.DigitalInOut(board.D6)
	oled = adafruit_ssd1306.SSD1306_SPI(WIDTH, HEIGHT, spi, oled_dc, oled_reset, oled_cs)

	# Clear display.
	oled.fill(0)
	oled.show()

	# Create blank image for drawing.
	# Make sure to create image with mode '1' for 1-bit color.
	image = Image.new("1", (oled.width, oled.height))

	# Get drawing object to draw on image.
	draw = ImageDraw.Draw(image)

	# Draw a white background
	draw.rectangle((0, 0, oled.width, oled.height), outline=255, fill=255)

	# Draw a smaller inner rectangle
	draw.rectangle(
    	(BORDER, BORDER, oled.width - BORDER - 1, oled.height - BORDER - 1),
    	outline=0,
    	fill=0,
	)

	# Load default font.
	font = ImageFont.load_default()
	print(msg.payload.decode("utf-8"))

	# This if statement will print out anything that is published while count is less than or equal to 2
	if (count <= 2):
		text = msg.payload.decode("utf-8")
		(font_width, font_height) = font.getsize(text)
		draw.text(
    		(oled.width // 2 - font_width // 2, oled.height // 2 - font_height // 2),
    		text,
    		font=font,
   		fill=255,
		)

		oled.image(image)
		oled.show()



	# This if statement will print out scrolling text when both players have finished their workout
	if (count == 3):  # When the players start another round of workouts the count variable will be reset so the text stops scrolling
		text = msg.payload
		(font_width, font_height) = font.getsize(text)

		for n in range(128, -130, -1):
			draw.text(
    				(n, oled.height // 2 - font_height // 2),
   	      			text,
    				font=font,
    				fill=255,
			)

			oled.image(image)
			oled.show()
			sleep(0.01)
			draw.rectangle(
				(BORDER, BORDER, oled.width - BORDER - 1, oled.height - BORDER - 1),
				outline = 0,
				fill = 0,
			)


# GPIO pins on the raspberry for the LED&KEY display
STB = 14
CLK = 15
DIO = 18

TM = TMBoards(DIO, CLK, STB, 0)
TM.clearDisplay()

num_left = 1234
num_right = 5678

workout = -1
count = 0
key = " "
result = 0
score = 0
message = " "
player = "f20v/Player2"

# GPIO pins on the raspberry for the buttons on the breadboard
yes_button = Button(16)
no_button = Button(20)
workout_button = Button(21)

workout_list = ["Push ups", "Pull ups", "Squats", "Split squats", "Crunches", "Burpees", "Plank", "Blg split squats"]

workouts = ["10 reps", "5 reps", "10 reps", "10 reps", "10 reps", "10 reps", "60 seconds", "10 reps"]

client = mqtt.Client()
client.on_connect = on_connect

# Functions assigned to the buttons
workout_button.when_pressed = press
yes_button.when_pressed = accept
no_button.when_pressed = decline

client.on_message = on_message
client.connect("test.mosquitto.org", 1883, 60)
client.loop_forever()

