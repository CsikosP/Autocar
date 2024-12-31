from flask import Flask, render_template, url_for, redirect
from gpiozero import Motor, AngularServo, TonalBuzzer, LEDBoard
from gpiozero.pins.pigpio import PiGPIOFactory
from gpiozero.tones import Tone
from time import sleep, time

app = Flask(__name__)

# Initial authorized state
authorized = False

# LED
leds = LEDBoard(16, 19)
led_states = {'green' : 0, 'red': 0}

factory = PiGPIOFactory(host='localhost')
servo = AngularServo(21, min_angle=0, max_angle=180, pin_factory=factory, min_pulse_width=0.0005, max_pulse_width=0.0024)
servo2 = AngularServo(25, min_angle=0, max_angle=180, pin_factory=factory, min_pulse_width=0.0005, max_pulse_width=0.0024)
servo3 = AngularServo(24, min_angle=0, max_angle=180, pin_factory=factory, min_pulse_width=0.0005, max_pulse_width=0.0024)
trunk_degrees = 0.0
door_degrees = 0.0

R_motor = Motor(forward=17, backward=18)
L_motor = Motor(forward=23, backward=22)
R_motor_speed = 1
L_motor_speed = 1

b = TonalBuzzer(26)
buzzer_states = 0

last_door_time = time()

@app.route('/')
def home():
    return render_template("index_autocar.html", R_motor_speed=R_motor_speed, L_motor_speed=L_motor_speed, trunk_degrees=trunk_degrees, door_degrees=door_degrees)

@app.route('/<wheel>/<int:wheel_speed>')
def wheel_sp(wheel, wheel_speed):
    global R_motor_speed, L_motor_speed  

    if wheel_speed == 1 and wheel == 'R':
        R_motor_speed = min(max(round(R_motor_speed + 0.1, 1), 0), 1)
    elif wheel_speed == 1 and wheel == 'L':
        L_motor_speed = min(max(round(L_motor_speed + 0.1, 1), 0), 1)
    elif wheel_speed == 1 and wheel == 'RL':
        R_motor_speed = min(max(round(R_motor_speed + 0.1, 1), 0), 1)
        L_motor_speed = min(max(round(L_motor_speed + 0.1, 1), 0), 1)
    elif wheel_speed == 0 and wheel == 'R':
        R_motor_speed = min(max(round(R_motor_speed - 0.1, 1), 0), 1)
    elif wheel_speed == 0 and wheel == 'L':
        L_motor_speed = min(max(round(L_motor_speed - 0.1, 1), 0), 1)
    elif wheel_speed == 0 and wheel == 'RL':
        R_motor_speed = min(max(round(R_motor_speed - 0.1, 1), 0), 1)
        L_motor_speed = min(max(round(L_motor_speed - 0.1, 1), 0), 1)
    
    return redirect(url_for('home'))

@app.route('/<move>')
def move_car(move):
    global R_motor_speed, L_motor_speed

    if move == 'stop':
        R_motor.stop()
        L_motor.stop()
    elif move == 'forward':
        if R_motor_speed > 0 or L_motor_speed > 0:  # Check if motors have a speed set for forward
            R_motor.forward(speed=R_motor_speed)
            L_motor.forward(speed=L_motor_speed)
            led_states['green'] = 1
            leds.value = tuple(led_states.values())
            sleep(0.1)  # Operate the motors for 0.2 seconds
            R_motor.stop()
            L_motor.stop()
            led_states['green'] = 0
            leds.value = tuple(led_states.values())
    elif move == 'backward':
        if R_motor_speed > 0 or L_motor_speed > 0:  # Check if motors have a speed set for backward
            R_motor.backward(speed=R_motor_speed)
            L_motor.backward(speed=L_motor_speed)
            led_states['red'] = 1
            leds.value = tuple(led_states.values())
            sleep(0.1)  # Operate the motors for 0.2 seconds
            R_motor.stop()
            L_motor.stop()
            led_states['red'] = 0
            leds.value = tuple(led_states.values())
    
    return redirect(url_for('home'))


@app.route('/all/<int:state>')
def all_led_switch(state):
    if state != 0:
        state = 1
        
    led_states['green'] = state
    led_states['red'] = state

    leds.value = tuple(led_states.values())

    return redirect(url_for('home'))

@app.route('/trunk/<int:trunk_state>')
def open_trunk(trunk_state):
    global trunk_degrees, last_command

    if trunk_state == 1:
        trunk_degrees = 60.0
        servo.angle = trunk_degrees
    elif trunk_state == 0:
        trunk_degrees = 0.0
        servo.angle = trunk_degrees
    sleep(0.05)

    return redirect(url_for('home'))

@app.route('/door/<int:door_state>')
def open_door(door_state):
    global door_degrees, last_door_time

    if door_state == 1:
        door_degrees = 90.0
        servo2.angle = door_degrees
        servo3.angle = 90 + door_degrees
    elif door_state == 0:
        door_degrees = 0.0
        servo2.angle = door_degrees
        servo3.angle = 90 + door_degrees
    sleep(0.05)

    return redirect(url_for('home'))

@app.route('/open_close_door')
def open_close_door():
    global door_degrees, last_door_time

    now = time()
    if door_degrees == 0 and now - last_door_time > 2.5:
        last_door_time = now
        return redirect(url_for('open_door', door_state = 1))
    elif door_degrees == 90.0 and now - last_door_time > 2.5:
        last_door_time = now
        return redirect(url_for('open_door', door_state = 0))
    else:
        return redirect(url_for('home'))
    
@app.route('/sound/<int:state>')
def sound_state(state):
    if state == 1:
        b.play(Tone('E4')) #미
    elif state == 0:
        b.stop()

    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(port=8064, host='0.0.0.0')