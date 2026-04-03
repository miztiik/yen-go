
function get_sgf_from_starting_position(go, tsumego, language) {
  var alpha = "abcdefghijklmnopqrstuvwxyz";
  var player_rank = language.get_short_rank(tsumego._rating);
  if (!player_rank) player_rank = "30k";
  var black_string = language.black;
  if (!black_string) black_string = "Black";
  var white_string = language.white;
  if (!white_string) white_string = "White";
  var result = "(;FF[4]CA[UTF-8]GM[1]US[blacktoplay.com]PB[" + black_string + "]PW[" + white_string + "]BR[" + player_rank + "]WR[" + player_rank + "]GN[" + tsumego._id + " - blacktoplay.com]TM[0]OT[60 simple]RE[?]";
  result += "SZ[" + tsumego._board_size + "]";

  if (go._player_to_move == "W") {
    var player = "W";
    var opponent = "B";
    var instruction_string = language.white_to_play;
  } else {
    var player = "B";
    var opponent = "W";
    var instruction_string = language.black_to_play;
  }

  if (!instruction_string) {
    instruction_string = "-";
  }

  var first_move = "";
  var ko = false;
  var extra_ko_stone = "";
  if (go._current_node.ko && go._current_node.ko != "-") {
    ko = true;
    extra_ko_stone = alpha[go._current_node.ko[0]] + alpha[go._current_node.ko[1]];
    if (!first_move) {
      // Find the one stone in atari around the ko point:
      var d = go.direction(go._current_node.ko[0], go._current_node.ko[1]);
      for (var i = 0; i < d.length; i += 1) {
        if (go.group_size(d[i][0], d[i][1], go._current_node.position) == 1 && go.liberties(d[i][0], d[i][1], go._current_node.position) == 1) {
          first_move = alpha[d[i][0]] + alpha[d[i][1]];
          break;
        }
      }
    }
  }

  result += "KM[" + tsumego._komi + "]";
  result += "RU[Chinese]";
  if (first_move) {
    result += "PL[" + opponent + "]";
  } else {
    result += "PL[" + player + "]";
  }

  var black_stones = "AB";
  var white_stones = "AW";
  for (var y = 0; y < go._current_node.position.length; ++y) {
    for (var x = 0; x < go._current_node.position[y].length; ++x) {
      var c = go._current_node.position[y][x];
      if (c == ".") {
        continue;
      }
      var coordinate = "" + alpha[x] + alpha[y];
      if (coordinate == first_move) {
        continue;
      }
      if (c == "B") black_stones += "[" + coordinate + "]";
      if (c == "W") white_stones += "[" + coordinate + "]";
    }
  }
  if (ko == true) {
    if (player == "B") {
      black_stones += "[" + extra_ko_stone + "]";
    } else {
      white_stones += "[" + extra_ko_stone + "]";
    }
  }
  result += black_stones + white_stones;
  if (ko == true) {
    var ko_string = language.sgf_ko_info;
    if (!ko_string) {
      ko_string = "-";
    }
    result += "C[" + ko_string + "]";
  } else {
    result += "C[" + instruction_string + "]";
  }
  result += ";";
  if (first_move) {
    result += opponent + "[" + first_move + "]C[" + instruction_string + "];";
  }
  result += ")";
  return result;
}


