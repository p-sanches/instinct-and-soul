PORT     ?=
CREATURE ?=

.PHONY: help flash repl reset ls tune spine

help:
	@echo "embodied-prompting — common dev commands"
	@echo ""
	@echo "Direct flash (replace main.py on a board):"
	@echo "  make flash CREATURE=creatures/touchy-pebble PORT=/dev/tty.usbmodem..."
	@echo ""
	@echo "Device shell:"
	@echo "  make repl  PORT=/dev/tty.usbmodem...    # interactive REPL"
	@echo "  make reset PORT=/dev/tty.usbmodem...    # soft-reset board"
	@echo "  make ls    PORT=/dev/tty.usbmodem...    # list files on board"
	@echo ""
	@echo "Run a tuner / spine on the laptop:"
	@echo "  make tune  CREATURE=creatures/touchy-pebble"
	@echo "  make spine CREATURE=creatures/touchy-pebble"

flash:
	@test -n "$(CREATURE)" || (echo "usage: make flash CREATURE=creatures/<name> PORT=/dev/..."; exit 1)
	@test -n "$(PORT)"     || (echo "usage: make flash CREATURE=creatures/<name> PORT=/dev/..."; exit 1)
	mpremote connect $(PORT) cp $(CREATURE)/main.py :main.py
	mpremote connect $(PORT) reset

repl:
	@test -n "$(PORT)" || (echo "usage: make repl PORT=/dev/..."; exit 1)
	mpremote connect $(PORT) repl

reset:
	@test -n "$(PORT)" || (echo "usage: make reset PORT=/dev/..."; exit 1)
	mpremote connect $(PORT) reset

ls:
	@test -n "$(PORT)" || (echo "usage: make ls PORT=/dev/..."; exit 1)
	mpremote connect $(PORT) ls

tune:
	@test -n "$(CREATURE)" || (echo "usage: make tune CREATURE=creatures/<name>"; exit 1)
	python $(CREATURE)/tune.py

spine:
	@test -n "$(CREATURE)" || (echo "usage: make spine CREATURE=creatures/<name>"; exit 1)
	python spine.py $(CREATURE)
