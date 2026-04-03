
Tsumego = function(p) {
  this.init(p);
};

Tsumego.prototype = {

  init: function(p) {
    this._alpha = "abcdefghijklmnopqrstuvwxyz";
    this._parent = p;
    this._type;
    this._id = 0;
    this._db = 0;
    this._board_size = 9;
    this._viewport_size = 9;
    this._position = [];
    this._hash = null;
    this._rating = 0;
    this._daily = false;
    this._current_date = false;
    this._stats = {"liked": 0, "attempted": 0, "cleared": 0};
    this._attempted = false;
    this._first_try = true;
    this._to_play = "B";
    this._komi = 0.5;
    this._prisoners = {"B": 0, "W": 0};
    this._ko = null;
    this._user = {"solved": false, "liked": 0, "starred": false};
    this._nodes = [];
    this._current_node = null;
    this._solved = false;
    this._timestamp = null;
    this._user_liked = 0;
    this.loaded = false;
    this.history = [];
    this.outside = true;
    this._loaded_from_discussion = false;
  },

  position_from_hash: function(hash, size) {
    var base = "0123456789abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ";
    var position_string = "";
    for(var n = 0; n < hash.length; n += 2) {
      var number = (base.indexOf(hash[n + 1]) * 59) + base.indexOf(hash[n]);
      var part = "";
      for(var i = 6; i > -1; --i) {
        if(number >= Math.pow(3, i)) {
          if(number >= (Math.pow(3, i) * 2)) {
            part = "W" + part;
            number -= (Math.pow(3, i) * 2);
          } else {
            part = "B" + part;
            number -= Math.pow(3, i);
          }
        } else {
          part = "." + part;
        }
      }
      position_string += part;
    }
    if(position_string.length > (size * size)) {
      position_string = position_string.substring(0, (size * size));
    }
    var position = [];
    for(var i = 0; i < size; ++i) {
      var row = position_string.substring(i * size, (i * size) + size);
      position.push(row);
    }
    // Pad position if visible is smaller than this._board_size:
    for (var y = 0; y < position.length; ++y) {
      while (position[y].length < size) position[y] += ".";
    }
    while(position.length < size) position.push(new Array(size + 1).join("."));
    return position;
  },

  load: function(data) {
    this.loaded = true;
    this._solved = false;
    this._first_try = true;
    this.history = ["aaaa"];
    this.outside = false;
    this._user_liked = 0;

    let invert_colors = false;
    if (data.to_play == "W") {
      invert_colors = true;
      let b_prisoners = data.prisoners["B"];
      data.prisoners["B"] = data.prisoners["W"];
      data.prisoners["W"] = b_prisoners;
      data.komi = data.komi * -1;
      if (data.to_play == "B") {
        data.to_play = "W";
      } else {
        data.to_play = "B";
      }
    }

    if (data.timestamp) {
      this._timestamp = data.timestamp;
    } else {
      this._timestamp = null;
    }

    if (data.daily && data.daily == true) {
      this._daily = true;
    } else {
      this._daily = false;
    }

    if (data.current_date && data.current_date == true) {
      this._current_date = true;
    } else {
      this._current_date = false;
    }

    if (data.type == 0) {
      this._type = "classic";
    } else if (data.type == 1) {
      this._type = "ai";
    } else if (data.type == 2) {
      this._type = "endgame";
    }
    this._id = data.id;
    if (data.hash) {
      this._hash = data.hash;
    } else {
      this._hash = null;
    }
    this._db = Number(data.db);
    this._rating = data.rating;
    this._nodes = [];
    var node_strings = data.nodes;
    for (node_string of node_strings) {
      split_string = node_string.split(";");
      var row = {
        "id": split_string[0],
        "parent": split_string[1],
        "ko": split_string[2],
        "correct_moves": split_string[3],
        "wrong_moves": split_string[4],
        "standard_response": split_string[5],
        "move_categories": split_string[6],
      };
      this._nodes.push(row);
    }
    this._current_node = this._nodes.find(k => k.id == "start");
    this._current_node.move_nr = 0;
    this._stats = {"liked": data.liked,
                   "attempted": data.attempted,
                   "cleared": data.cleared};
    this._tags = data.tags;
    this._categories = data.categories;
    this._attempted = false;
    // Todo: Add these parameters?
    //this._user = {"solved": data.user_solved,
    //              "liked": data.user_liked};

    if (this._type == "classic") {
      var position_part = this.position_from_hash(data.hash, data.viewport_size);
      this._position = [];
      for(var row of position_part) {
        this._position.push(row);
        while (this._position[this._position.length - 1].length < data.board_size) {
          this._position[this._position.length - 1] += ".";
        }
      }
      while (this._position.length < data.board_size) {
        var padding = "";
        while (padding.length < data.board_size) {
          padding += ".";
        }
        this._position.push(padding);
      }
    } else {
      this._position = this.copy_array(this.position_from_hash(data.hash, data.board_size));
    }
    if (invert_colors == true) {
      this.invert_position_colors(this._position);
      this._hash = this.get_hash_from_position(this._position, data.viewport_size);
      data.hash = this._hash;
    }
    this._board_size = data.board_size;
    this._viewport_size = data.viewport_size;
    this._to_play = data.to_play;
    this._komi = data.komi;
    this._prisoners = data.prisoners;
    var start_node = this._nodes.find(k => k.id == "start");
    if(start_node && start_node.ko && start_node.ko.length > 1) {
      var ko_coordinates = start_node.ko.split("-");
      this._ko = [parseInt(ko_coordinates[0]), parseInt(ko_coordinates[1])];
    } else {
      this._ko = start_node.ko;
    }
    this._comments = data.comments;

    //
    // Parse correct/wrong moves in all nodes
    //

    go = new Go(this._board_size, this._komi);
    go.load(this._board_size, this._position, this._komi, this._ko, this._prisoners, this._to_play);
    this.recursive_parse(this._current_node, go);

    //
    //
    //

    if (this._type != "classic") {
      this._sgf = get_sgf_from_starting_position(go, this, global.language._active_language);
    } else {
      this._sgf = null;
    }

    cookie_handler.update_data("last_type", this._type);

  },

  invert_position_colors: function(position) {
    for (let n = 0; n < position.length; ++n) {
      position[n] = position[n].replaceAll("B", "@");
    }
    for (let n = 0; n < position.length; ++n) {
      position[n] = position[n].replaceAll("W", "B");
    }
    for (let n = 0; n < position.length; ++n) {
      position[n] = position[n].replaceAll("@", "W");
    }
  },


  get_hash_from_position: function(input_position, visible) {
    var result = "";
    const chars = ".BW";
    const base_59 = "0123456789abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ";
    var position = "";
    for (var y = 0; y < visible; ++y) {
      for (var x = 0; x < visible; ++x) {
        position += input_position[y][x];
      }
    }
    for (var i = 0; i < position.length; i += 7) {
      var number = 0;
      for (var c = 0; c < 7; ++c) {
        if ((i + c) < position.length) {
          number += (chars.indexOf(position[i + c]) * Math.pow(3, c));
        }
      }
      result += base_59[number % 59] + base_59[((number - (number % 59)) / 59)];
    }
    return result;
  },

  recursive_parse: function(node, go) {
    if (node.parsed && node.parsed == true) return;
    var correct_string = node.correct_moves;
    var category_strings = node.move_categories.split("|");
    var lowest_move_rating = 10000;
    var correct_list = [];
    var i = 0;
    var cs_index = 0;
    while (i < correct_string.length) {
      var item = {};
      item.move = correct_string.substring(i, i + 2);
      if(correct_string[i + 2] == "-") {
        item.response = "-";
        i += 3;
      } else {
        item.response = correct_string.substring(i + 2, i + 4).toLowerCase();
        i += 4
      }
      var node_name = "";
      while(correct_string[i] != "T" && correct_string[i] != "F") {
        node_name += correct_string[i];
        ++i;
      }
      item.child = node_name;
      if(correct_string[i] == "T") {
        item.end = true;
      } else {
        item.end = false;
      }
      // Parse move_categories:
      var category_rating_string = "";
      var n = 0;
      while(!isNaN(category_strings[cs_index][n])) {
        category_rating_string += category_strings[cs_index][n];
        ++n;
      }
      if(category_rating_string < lowest_move_rating) {
        lowest_move_rating = Number(category_rating_string);
      }
      item.rating = Number(category_rating_string);
      item.categories = [];
      while(n < category_strings[cs_index].length) {
        var category = STATIC_CATEGORIES["ABCDEFGHIJKLMNOPQRSTUVWXYZ".indexOf(category_strings[cs_index][n])];
        if(!item.categories.includes(category)) {
          item.categories.push(category);
        }
        ++n;
      }
      ++cs_index;
      //
      correct_list.push(item);
      ++i;
    }
    node.correct_moves = correct_list;
    if(lowest_move_rating != 10000) {
      node.lowest_move_rating = lowest_move_rating;
    } else {
      node.lowest_move_rating = null;
    }

    // List categories which are present in all correct moves:
    var potential_categories = []
    for(var cm of node.correct_moves) {
      for(c of cm.categories) {
        if(!potential_categories.includes(c)) {
          potential_categories.push(c);
        }
      }
    }
    for(var i = 0; i < potential_categories.length; ++i) {
      for(var cm of node.correct_moves) {
        if(!cm.categories.includes(potential_categories[i])) {
          potential_categories.splice(i, 1);
          i--;
          break;
        }
      }
    }
    node.common_categories = potential_categories;
    //

    wrong_string = node.wrong_moves;
    counter = 0;
    if(!isNaN(wrong_string[0])) {
      var i = 0;
      num = "";
      while(!isNaN(wrong_string[i])) {
        num += wrong_string[i];
        ++i;
      }
      wrong_string = wrong_string.substring(num.length);
      counter = parseInt(num);
    }

    wrong_list = [];
    saved_responses = {"response": "", "counter": 0}
    for(var y = 0; y < this._viewport_size; ++y) {
      for(var x = 0; x < this._viewport_size; ++x) {
        coordinate = String.fromCharCode(97 + x) + String.fromCharCode(97 + y);
        // NOTE: It is always the same color at each node,
        //       that is why we can use this._to_play instead of go._player_to_move
        if(!go.legal(x, y, this._to_play) || node.correct_moves.find(k => k.move == coordinate)) {
          continue;
        }
        if(saved_responses["counter"] > 0) {
          // console.log("Adding move: " + coordinate + " and response: " + saved_responses["response"]);
          wrong_list.push({"move": coordinate, "response": saved_responses["response"]});
          saved_responses["counter"] -= 1;
          continue;
        }
        if(counter == 0 && wrong_string.length > 0) {
          if(isNaN(wrong_string[0])) {
            if(wrong_string[0] == "-") {
              wrong_string = wrong_string.substring(1);
              continue;
            }
            var response = wrong_string.substring(0, 2);
            wrong_string = wrong_string.substring(2);
            if(response.charCodeAt(0) < 97 || response.charCodeAt(1) < 97) { // One or more upper case letters
              var number = 0;
              if(response.charCodeAt(0) < 97) {
                number += 2;
              }
              if(response.charCodeAt(1) < 97) {
                number += 1;
              }
              response = response.toLowerCase();
              saved_responses["response"] = response;
              saved_responses["counter"] = number;
            }
            wrong_list.push({"move": coordinate, "response": response});
          } else {
            var i = 0;
            num = "";
            while(!isNaN(wrong_string[i])) {
              num += wrong_string[i];
              ++i;
            }
            wrong_string = wrong_string.substring(num.length);
            counter = parseInt(num - 1);
	    if(this._type != "classic") {
              wrong_list.push({"move": coordinate, "response": node.standard_response});
	    }
          }
        } else {
	  if (this._type != "classic") {
            wrong_list.push({"move": coordinate, "response": node.standard_response});
	  }
          counter--;
        }
      }
    }
    node.wrong_moves = wrong_list;

    for(cm of node.correct_moves) {
      if(cm.end == false) {
        go.play_move(cm.move.charCodeAt(0) - 97, cm.move.charCodeAt(1) - 97);
        go.play_move(cm.response.charCodeAt(0) - 97, cm.response.charCodeAt(1) - 97);
        var next_node = this._nodes.find(k => k.id == cm.child);
        this.recursive_parse(next_node, go);
        go.step_back();
        go.step_back();
      }
    }

    delete(node.move_categories);
    node.parsed = true;

  },

  get_daily: function() {
    return this._daily;
  },

  get_current_date: function() {
    return this._current_date;
  },

  get_db: function() {
    return this._db;
  },

  get_id: function() {
    if (this._type == "classic") {
      return Number(this._id);
    } else {
      return this._id;
    }
  },

  get_rating: function() {
    return this._rating;
  },

  get_hash: function() {
    return this._hash;
  },

  get_liked: function() {
    return this._stats.liked;
  },

  increment_liked: function() {
    if (this._user_liked < 1) {
      this._stats.liked++;
      this._user_liked++;
    }
  },

  decrement_liked: function() {
    if (this._user_liked > -1) {
      this._stats.liked--;
      this._user_liked--;
    }
  },

  get_attempted: function() {
    return this._stats.attempted;
  },

  increment_attempted: function() {
    this._stats.attempted++;
  },

  increment_cleared: function() {
    this._stats.cleared++;
  },

  get_cleared: function() {
    return this._stats.cleared;
  },

  get_type: function() {
    return this._type;
  },

  get_board_size: function() {
    return this._board_size;
  },

  get_viewport_size: function() {
    return this._viewport_size;
  },

  get_position: function() {
    return this.copy_array(this._position);
  },

  get_komi: function() {
    return this._komi;
  },

  get_ko: function() {
    return this._ko;
  },

  get_prisoners: function() {
    return this._prisoners;
  },

  get_color: function() {
    return this._to_play;
  },

  get_moves: function(id) {
    if(!this.loaded) return null;
    var result = {"correct_moves": [], "wrong_moves": []};
    if(!this.outside || id == this.history[this.history.length - 1]) {
      if(this.history.length % 2) {
        for(var i = 0; i < this._current_node.correct_moves.length; ++i) {
          result.correct_moves.push(this._current_node.correct_moves[i].move);
        }
        for(var i = 0; i < this._current_node.wrong_moves.length; ++i) {
          result.wrong_moves.push(this._current_node.wrong_moves[i].move);
        }
      } else {
        var response = this.get_response(this._current_node.move);
        if(response.response) {
          if(response.correct) {
            result.correct_moves.push(response.response);
          } else {
            result.wrong_moves.push(response.response);
          }
        }
      }
    }
    return result;
  },

  step_forward: function(move, id) {
    if(this.history.length % 2) {
      var response = this.get_response(move);
      if(response.correct) {
        if (response.end) {
          this.outside = true;
        }
      } else {
        this.outside = true;
      }
      this.history.push(id);
    } else {
      var response = this.get_response(this._current_node.move);
      if (!this.outside && response.correct && !response.end && response.response == move) {
        var node = this._nodes.find(k => k.id == response.child);
        if (node) this._current_node = node;
        this.history.push(id);
      } else {
        this.outside = true;
      }
    }
  },

  step_back: function(id) {
    if(this.outside) {
      if(id == this.history[this.history.length - 1]) {
        // Exit point
        this.outside = false;
      } else if(id == this.history[this.history.length - 2]) {
        this.outside = false;
        this.history.pop();
      }
    } else {
      if((this.history.length % 2) == 1) {
        var node = this._nodes.find(k => k.id == this._current_node["parent"]);
        if(node) this._current_node = node;
      }
      this.history.pop();
    }
  },

  play_move: function(move, id) {
    if(!this._attempted) {
      this._attempted = true;
      this.increment_attempted();
      global.solver._info.update_attempted_and_cleared(this._stats);
      global.tsumego_list.move_item_to_attempted(this._id, this._type, this._rating);
      global.connection.update_attempts(this._id, this._db);
      global.tsumego_list._attempted_in_current_list++;
    }
    if(this.history.length % 2) {
      this.player_move(move, id);
    } else {
      this.opponent_move(move, id);
    }
  },

  player_move: function(move, id) {
    this._current_node.move = move;
    var response = this.get_response(move);
    if (!this._solved && this._first_try) {
      global.player.update_move_statistics(response.correct, response.categories, response.rating, this._rating);
    }
    if(response.correct) {
      this.history.push(id);
      if (response.end) {
        this.outside = true;
        if(this._solved == false) {
          this._solved = true;
          this._parent.signal_tsumego_solved(this._first_try);
          global.noice.play("pling");
        } else {
          global.noice.play("click");
        }
      } else {
        global.noice.play("click");
        if(!this._solved) {
          setTimeout(() => {this._parent.signal_move(response.response, "auto");}, 280);
        }
      }
    } else {
      if(this._first_try) {
        this._first_try = false;
        this._parent.signal_wrong_solution();
      } else if (this._loaded_from_discussion) {
        this._parent.signal_wrong_solution_for_discussion_item();
        this._loaded_from_discussion = false;
      }
      this.outside = true;
      this.history.push(id);
      if(!this._solved) {
        global.noice.play("wrong");
        if(response.response) {
          setTimeout(() => {this._parent.signal_move(response.response, "auto");}, 280);
        }
      } else {
        global.noice.play("click");
      }
    }
  },

  opponent_move: function(move, id) {
    global.noice.play("click");
    if(!this.outside) {
      var correct_move = false;
      for(var i = 0; i < this._current_node.correct_moves.length; ++i) {
        if(this._current_node.correct_moves[i].response == move && this._current_node.correct_moves[i].move == this._current_node.move) {
          correct_move = true;
        }
      }
      if(!correct_move) {
        this.outside = true;
        return;
      }
    }
    var response = this.get_response(this._current_node.move);
    if (response.correct && !response.end && response.response == move) {
      var node = this._nodes.find(k => k.id == response.child);
      if (node) {
        var previous_move_number = this._current_node.move_nr;
        this._current_node = node;
        this._current_node.move_nr = previous_move_number + 2;
      }
    }
    this.history.push(id);
  },

  get_response: function(move) {
    var result = {"response": null, "correct": false, "child": null, "end": false}; 
    for(var i = 0; i < this._current_node.correct_moves.length; ++i) {
      if(this._current_node.correct_moves[i].move == move) {
        result.correct = true;
        result.response = this._current_node.correct_moves[i].response;
        result.child = this._current_node.correct_moves[i].child;
        result.end = this._current_node.correct_moves[i].end;
        result.categories = this._current_node.correct_moves[i].categories;
        result.rating = this._current_node.correct_moves[i].rating;
      }
    }
    for(var i = 0; i < this._current_node.wrong_moves.length; ++i) {
      if(this._current_node.wrong_moves[i].move == move) {
        result.response = this._current_node.wrong_moves[i].response;
        result.categories = this._current_node.common_categories;
        result.rating = this._current_node.lowest_move_rating;
      }
    }
    if(!result.response) {
      // NOTE: standard_response is only used for classic tsumego
      if(this._current_node.standard_response && this._current_node.standard_response.length == 2 && this._type == "classic") {
        result.response = this._current_node.standard_response;
        result.categories = this._current_node.common_categories;
        result.rating = this._current_node.lowest_move_rating;
      }
    }
    if(!result.categories || !result.rating) {
      result.categories = this._current_node.common_categories;
      result.rating = this._current_node.lowest_move_rating;
    }
    return result;
  },

  copy_array: function(arr) {
    var result = [];
    for (var i = 0; i < arr.length; i += 1) {
      result.push(arr[i]);
    }
    return result;
  },

};


