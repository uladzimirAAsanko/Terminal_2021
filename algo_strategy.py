import gamelib
import random
import math
import warnings
from sys import maxsize
import json


"""
Most of the algo code you write will be in this file unless you create new
modules yourself. Start by modifying the 'on_turn' function.

Advanced strategy tips: 

  - You can analyze action frames by modifying on_action_frame function

  - The GameState.map object can be manually manipulated to create hypothetical 
  board states. Though, we recommended making a copy of the map to preserve 
  the actual current map state.
"""

class AlgoStrategy(gamelib.AlgoCore):
    def     __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))

    def on_game_start(self, config):
        """ 
        Read in config and perform any initial setup here 
        """
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        global WALL, SUPPORT, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR, MP, SP, OUR_FIELD, ARR_FIELD
        WALL = config["unitInformation"][0]["shorthand"]
        SUPPORT = config["unitInformation"][1]["shorthand"]
        TURRET = config["unitInformation"][2]["shorthand"]
        SCOUT = config["unitInformation"][3]["shorthand"]
        DEMOLISHER = config["unitInformation"][4]["shorthand"]
        INTERCEPTOR = config["unitInformation"][5]["shorthand"]
        ARR_FIELD = [1000] * 27
        for i in range(27):
            ARR_FIELD[i] = [1000] * 27
        for i in range(14):
            for j in range(i):
                ARR_FIELD[13 - j][i] = 0
                ARR_FIELD[14 + j][i] = 0
        OUR_FIELD = []
        for i in range(14):
            for j in range(i):
                OUR_FIELD.append([13 - j, i])
                OUR_FIELD.append([14 + j, j])
        MP = 1
        SP = 0
        # This is a good place to do initial setup

        self.scored_on_locations = []

    def on_turn(self, turn_state):
        """in_arena_bounds
        This function is called every turn with the game state wrapper as
        an argument. The wrapper stores the state of the arena and has methods
        for querying its state, allocating your current resources as planned
        unit deployments, and transmitting your intended deployments to the
        game engine.
        """
        game_state = gamelib.GameState(self.config, turn_state)
        game_state.suppress_warnings(True)  #Comment or remove this line to enable warnings.

        self.starter_strategy(game_state)

        game_state.submit_turn()

    def mark_def_point(self, game_state, turrets_placed):
        for turret in turrets_placed:
            gamelib.debug_write(str(turret))
            self.mark_around_turrel(game_state, turret)

    def mark_around_turrel(self, game_state, location):
        if not gamelib.game_map.GameMap.in_arena_bounds(game_state.game_map, location):
            return False
        for i in range(27):
            gamelib.debug_write( str(ARR_FIELD[i]))
        ARR_FIELD[location[0]][location[1]] += 1
        location_in_range = game_state.game_map.get_locations_in_range(location, 3.5)
        for loco in location_in_range:
            ARR_FIELD[loco[0]][loco[1]] += 1
        return True

    def choose_best_tower_loco(self, game_state):
        minimal_vage = 100
        for i in range(27):
            if minimal_vage < ARR_FIELD[i][12]:
                minimal_vage = ARR_FIELD[i][12]
        best_loco = []
        for i in range(27):
            if minimal_vage == ARR_FIELD[i][12]:
                best_loco.append([i, 12])
        sum_of_points = []
        for location in best_loco:
            location_in_range = game_state.game_map.get_locations_in_range(location, 3.5)
            sum_of_loco = 1
            count_of_parts = 1
            for loco in location_in_range:
                if gamelib.game_map.GameMap.in_arena_bounds(game_state.game_map, loco):
                    sum_of_loco += ARR_FIELD[loco[0]][loco[1]]
                    count_of_parts += 1
            sum_of_points.append(sum_of_loco/count_of_parts)
        max_sum = 0
        index = 0
        for sum in sum_of_points:
            if max_sum < sum:
                index = sum_of_points.index(sum)
                max_sum = sum
        return best_loco[index]


    """
    NOTE: All the methods after this point are part of the sample starter-algo
    strategy and can safely be replaced for your custom algo.
    """

    def starter_strategy(self, game_state):
        """
        For defense we will use a spread out layout and some interceptors early on.
        We will place turrets near locations the opponent managed to score on.
        For offense we will use long range demolishers if they place stationary units near the enemy's front.
        If there are no stationary units to attack in the front, we will send Scouts to try and score quickly.
        """
        # First, place basic defenses
        if game_state.turn_number < 1:
            self.build_defences(game_state)
        # Now build reactive defenses based on where the enemy scored

        placed_units = self.get_blocked_locations(OUR_FIELD, game_state)
        turrels_placed = []
        supports_placed = []
        walls_placed = []
        for location in placed_units:
            unit = game_state.contains_stationary_unit(location)
            string_unit = str(unit)
            if string_unit.find("Friendly DF") != -1:
                turrels_placed.append(location)
            else:
                if string_unit.find("Friendly EF") != -1:
                    supports_placed.append(location)
                else:
                    walls_placed.append(location)
        self.mark_def_point(game_state, turrels_placed)

        # If the turn is less than 5, stall with interceptors and wait to see enemy's base

        best_loco = self.choose_best_tower_loco(game_state)
        if game_state.SP >= 8:
            game_state.attempt_spawn(TURRET, best_loco)
            game_state.attempt_upgrade(best_loco)
            best_loco[1] += 1
            game_state.attempt_spawn(WALL, best_loco)
            game_state.attempt_upgrade(best_loco)
        else:
            game_state.attempt_spawn(INTERCEPTOR, [22, 8], 2)
            game_state.attempt_spawn(INTERCEPTOR, [5, 8], 2)
        if game_state.MP >= 9:
            game_state.attempt_spawn(DEMOLISHER, [23, 9], 3)



    def build_defences(self, game_state):
        """
        Build basic defenses using hardcoded locations.
        Remember to defend corners and avoid placing units in the front where enemy demolishers can attack them.
        """
        # Useful tool for setting up your base locations: https://www.kevinbai.design/terminal-map-maker
        # More community tools available at: https://terminal.c1games.com/rules#Download

        # Place turrets that attack enemy units
        turret_locations = [[3, 12], [14, 12], [24, 12]]
        wall_locations = [[3, 13], [14, 13], [24, 13]]
        support_locations = [[9, 10], [18, 10]]
        # attempt_spawn will try to spawn units if we have resources, and will check if a blocking unit is already there
        game_state.attempt_spawn(TURRET, turret_locations)
        game_state.attempt_spawn(SUPPORT, support_locations)

        # Place walls in front of turrets to soak up damage for them
        game_state.attempt_spawn(WALL, wall_locations)
        # upgrade walls so they soak more damage
        game_state.attempt_upgrade(wall_locations)
        game_state.attempt_upgrade(support_locations)
        game_state.attempt_upgrade(turret_locations)

    def build_reactive_defense(self, game_state):
        """
        This function builds reactive defenses based on where the enemy scored on us from.
        We can track where the opponent scored by looking at events in action frames 
        as shown in the on_action_frame function
        """
        for location in self.scored_on_locations:
            # Build turret one space above so that it doesn't block our own edge spawn locations
            build_location = [location[0], location[1]+1]
            game_state.attempt_spawn(TURRET, build_location)

    def stall_with_interceptors(self, game_state):
        """
        Send out interceptors at random locations to defend our base from enemy moving units.
        """
        # We can spawn moving units on our edges so a list of all our edge locations
        friendly_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) + game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
        
        # Remove locations that are blocked by our own structures 
        # since we can't deploy units there.
        deploy_locations = self.filter_blocked_locations(friendly_edges, game_state)
        
        # While we have remaining MP to spend lets send out interceptors randomly.
        while game_state.get_resource(MP) >= game_state.type_cost(INTERCEPTOR)[MP] and len(deploy_locations) > 0:
            # Choose a random deploy location.
            deploy_index = random.randint(0, len(deploy_locations) - 1)
            deploy_location = deploy_locations[deploy_index]
            
            game_state.attempt_spawn(INTERCEPTOR, deploy_location)
            """
            We don't have to remove the location since multiple mobile 
            units can occupy the same space.
            """

    def demolisher_line_strategy(self, game_state):
        """
        Build a line of the cheapest stationary unit so our demolisher can attack from long range.
        """
        # First let's figure out the cheapest unit
        # We could just check the game rules, but this demonstrates how to use the GameUnit class
        stationary_units = [WALL, TURRET, SUPPORT]
        cheapest_unit = WALL
        for unit in stationary_units:
            unit_class = gamelib.GameUnit(unit, game_state.config)
            if unit_class.cost[game_state.MP] < gamelib.GameUnit(cheapest_unit, game_state.config).cost[game_state.MP]:
                cheapest_unit = unit

        # Now let's build out a line of stationary units. This will prevent our demolisher from running into the enemy base.
        # Instead they will stay at the perfect distance to attack the front two rows of the enemy base.
        for x in range(27, 5, -1):
            game_state.attempt_spawn(cheapest_unit, [x, 11])

        # Now spawn demolishers next to the line
        # By asking attempt_spawn to spawn 1000 units, it will essentially spawn as many as we have resources for
        game_state.attempt_spawn(DEMOLISHER, [24, 10], 1000)

    def least_damage_spawn_location(self, game_state, location_options):
        """
        This function will help us guess which location is the safest to spawn moving units from.
        It gets the path the unit will take then checks locations on that path to 
        estimate the path's damage risk.
        """
        damages = []
        # Get the damage estimate each path will take
        for location in location_options:
            path = game_state.find_path_to_edge(location)
            damage = 0
            for path_location in path:
                # Get number of enemy turrets that can attack each location and multiply by turret damage
                damage += len(game_state.get_attackers(path_location, 0)) * gamelib.GameUnit(TURRET, game_state.config).damage_i
            damages.append(damage)
        
        # Now just return the location that takes the least damage
        return location_options[damages.index(min(damages))]

    def detect_enemy_unit(self, game_state, unit_type=None, valid_x = None, valid_y = None):
        total_units = 0
        for location in game_state.game_map:
            if game_state.contains_stationary_unit(location):
                for unit in game_state.game_map[location]:
                    if unit.player_index == 1 and (unit_type is None or unit.unit_type == unit_type) and (valid_x is None or location[0] in valid_x) and (valid_y is None or location[1] in valid_y):
                        total_units += 1
        return total_units
        
    def filter_blocked_locations(self, locations, game_state):
        filtered = []
        for location in locations:
            if not game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered

    def get_blocked_locations(selfs, locations, game_state):
        filtered = []
        for location in locations:
            if game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered


    def on_action_frame(self, turn_string):
        """
        This is the action frame of the game. This function could be called 
        hundreds of times per turn and could slow the algo down so avoid putting slow code here.
        Processing the action frames is complicated so we only suggest it if you have time and experience.
        Full doc on format of a game frame at in json-docs.html in the root of the Starterkit.
        """
        # Let's record at what position we get scored on
        state = json.loads(turn_string)
        events = state["events"]
        breaches = events["breach"]
        for breach in breaches:
            location = breach[0]
            unit_owner_self = True if breach[4] == 1 else False
            # When parsing the frame data directly, 
            # 1 is integer for yourself, 2 is opponent (StarterKit code uses 0, 1 as player_index instead)
            if not unit_owner_self:
                gamelib.debug_write("Got scored on at: {}".format(location))
                self.scored_on_locations.append(location)
                gamelib.debug_write("All locations: {}".format(self.scored_on_locations))


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
