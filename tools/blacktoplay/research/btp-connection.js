
Connection = function(language) {
  this.init(language);
};

Connection.prototype = {

  init: function(language) {
    this._language = language;
    this._current_poll_id = "-";
    this._poll_interval = 360000; // 360_000 milliseconds = 6 min
  },

  generate_random_identifier: function() {
    let result = "";
    let base = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
    for (let i = 0; i < 16; ++i) {
      result += base[Math.floor(Math.random() * 62)];
    }
    return result;
  },

  start_poll: function(interval) {
    if (interval && !isNaN(interval)) {
      this.set_poll_interval(interval);
    }
    let poll_id = this.generate_random_identifier();
    this._current_poll_id = poll_id;
    this.load_notifications(poll_id);
  },

  is_poll_running: function() {
    if (this._current_poll_id == "-") return false;
    return true;
  },

  start_poll_based_on_timestamp: function(timestamp) {
    let interval = this.get_interval_based_on_timestamp(timestamp);
    this.start_poll(interval);
  },

  get_interval_based_on_timestamp: function(timestamp) {
    if (timestamp.length == 19) {
      timestamp = timestamp.replace(" ", "T") + ".000Z";
    } else if (timestamp.length != 24) {
      return 360000;
    }
    const now = new Date();
    const timestamp_time = new Date(timestamp);
    const diff_in_seconds = Math.round((now - timestamp_time) / 1000);
    let poll_time = 360000;
    if (diff_in_seconds < 1800) {
      // First 30 minutes, poll every minute
      poll_time = 60000;
    } else if (diff_in_seconds < 7200) {
      // First two hours, poll every two minutes
      poll_time = 120000;
    } else if (diff_in_seconds < 172800) {
      // First two days, poll every three minutes
      poll_time = 180000;
    } else if (diff_in_seconds < 432000) {
      // First five days, poll every four minutes
      poll_time = 240000;
    } else {
      // Else, poll every six minutes
      poll_time = 360000;
    }
    return poll_time;
  },

  poll_callback: function(poll_id) {
    if (poll_id && poll_id.length == 16) {
      if (global.player.get_last_comment && this._poll_interval != this.get_interval_based_on_timestamp(global.player.get_last_comment())) {
        this.set_poll_interval(this.get_interval_based_on_timestamp(global.player.get_last_comment()));
      }
      setTimeout(() => {
        this.load_notifications(poll_id);
      }, this._poll_interval);
    }
  },

  set_poll_interval: function(interval) {
    if (!isNaN(interval)) {
      this._poll_interval = interval;
    }
  },

  stop_poll: function() {
    this._current_poll_id = "-";
    this._poll_interval = 360000;
  },

  session_key_callback: function(status_message) {
    if (!status_message.includes("SESSION_KEY")) return false;
    if (status_message.includes("key_format")) {
      console.log("Wrong format of session_key");
      global.notice.message(global.connection._language._active_language.logged_out, 3000, 2);
      global.right_menu.set_button_text_to_login();
      global.left_menu.set_logo_block_to_login();
      global.signal_user_logged_out();
      global.signal_hide_admin_tools();
      global.player.set_admin(false);
    } else if (status_message.includes("key_invalid")) {
      global.notice.message(global.connection._language._active_language.logged_out, 6000, 1);
      global.right_menu.set_button_text_to_login();
      global.left_menu.set_logo_block_to_login();
      global.signal_user_logged_out();
      global.signal_hide_admin_tools();
      global.player.set_admin(false);
    } else if (status_message.includes("key_expired")) {
      global.notice.message(global.connection._language._active_language.logged_out_key_expired, 6000, 1);
      global.right_menu.set_button_text_to_login();
      global.left_menu.set_logo_block_to_login();
      global.signal_user_logged_out();
      global.signal_hide_admin_tools();
      global.player.set_admin(false);
    } else if (status_message.includes("ip_agent")) {
      global.notice.message(global.connection._language._active_language.logged_out, 6000, 1);
      global.right_menu.set_button_text_to_login();
      global.left_menu.set_logo_block_to_login();
      global.signal_user_logged_out();
      global.signal_hide_admin_tools();
      global.player.set_admin(false);
    } else if (status_message.includes("key_validation")) {
      global.notice.message(global.connection._language._active_language.logged_out, 6000, 1);
      global.right_menu.set_button_text_to_login();
      global.left_menu.set_logo_block_to_login();
      global.signal_user_logged_out();
      global.signal_hide_admin_tools();
      global.player.set_admin(false);
    }
  },

  ajax_callback: function(handle, data=null) {

    if (handle == "public_tsumego_list_loaded") {
      if (data) {
        // cookie_handler.update_data("raw_list", data.raw);
        global.signal_list_loaded(data);
      }
    }

    if (handle == "user_tsumego_list_loaded") {
      if (data) {
        // cookie_handler.update_data("raw_list", data.raw);
        global.signal_list_loaded(data);
      }
    }

    if (handle == "tsumego_data_loaded") {
      if (data) {
        global.signal_tsumego_loaded(data);
      }
    }

    if (handle == "tsumego_loading_failed") {
      if (app_fully_loaded == false) {
        loading_cover.update_progress();
        app_fully_loaded = true;
      }
      if(!global.solver._mini_icons._active) {
        global.solver._mini_icons.activate();
      }
      if(!global.solver._next_button.active) {
        global.solver._next_button.toggle();
      }
      if (data && data.discussion_item && data.discussion_item.reference && String(data.discussion_item.reference) == data.discussion_item.reference && data.discussion_item.reference.length == 6) {
        if (global.solver && global.solver._comments.discussion_modal_visible() == false) {
          global.solver._comments.show_discussion_modal();
        }
      }
    }

    if (handle == "tsumego_info_gotten") {
      if (data) {
        for (let i = 0; i < data.list.length; ++i) {
          if (data.list[i].to_play == "W") {
            if (global.solver._tsumego.invert_position_colors && global.solver._tsumego.get_hash_from_position) {
              let tsumego_position = global.solver._tsumego.position_from_hash(data.list[i].hash, data.list[i].viewport_size);
              global.solver._tsumego.invert_position_colors(tsumego_position);
              let inverted_hash = global.solver._tsumego.get_hash_from_position(tsumego_position, data.list[i].viewport_size);
              if (inverted_hash) {
                data.list[i].hash = inverted_hash;
                data.list[i].to_play = "B";
              }
            }
          } 
        }
        if (data.type == "history") {
          global.player.add_additional_info_to_user_history(data);
        } else if (data.type == "favorites") {
          global.player.add_additional_info_to_user_favorites(data);
        }
      }
    }

    if (handle == "daily_tsumego_loaded") {
      if (data) {
        global.signal_tsumego_loaded(data);
        if (global.left_menu.visible() == true) {
          global.signal_toggle_side_menu("left");
        }
      }
    }

    if (handle == "daily_info_loaded") {
      if (data) {
        if (data.from_url_path && data.from_url_path == true) {
          this.load_daily_tsumego(data.tsumego_id);
        } else {
          global.left_menu.add_daily_board(data);
        }
      }
    }

    if (handle == "code_verified") {
      if (data) {
        if (data.status == "success" && "username" in data && ("collection" in data)) {
          if (data.collection == 1) {
            if ("reference" in data && data.reference.length > 26 && "client_secret" in data) {
              // Show payment module
              global.payment.set_registration_reference(data.reference);
              global.login_modal.load_payment_registration_step();
              global.login_modal.hide_register_loading_cover();
              var current_spinner_object = document.getElementById("btp-register-modal-payment-spinner-container");
              current_spinner_object.style.display = "flex";
              current_spinner_object.style.visibility = "visible";
              current_spinner_object.style.opacity = 1;
              global.payment.load_payment_block("registration", data.client_secret);
            } else {
              global.notice.message(global.connection._language._active_language.could_not_verify_code, 4000, 1);
              global.login_modal.hide_register_loading_cover();
            }
          } else {
            global.login_modal._registration_step = 1; // Dirty fix to not show the floating link when completing registration
            global.login_modal.hide_register_modal();
            global.login_modal.show_success_modal(data.username);
            global.login_modal.clear_sign_up_form();
            setTimeout(() => {
              global.login_modal.load_first_registration_step();
            }, 400);
          }
        } else if (data.status == "wrong_code") {
          global.notice.message(global.connection._language._active_language.wrong_code, 3000, 1);
          global.login_modal.hide_register_loading_cover();
        } else if (data.status == "too_many_attempts") {
          global.notice.message(global.connection._language._active_language.too_many_attempts, 3000, 1);
          global.login_modal.hide_register_loading_cover();
        } else {
          global.notice.message(global.connection._language._active_language.could_not_verify_code, 4000, 1);
          global.login_modal.hide_register_loading_cover();
        }
      }
    }

    if (handle == "payment_skipped") {
      if (data) {
        if (data.status == "success" && "username" in data) {
          global.login_modal._registration_step = 1; // Dirty assignment for not showing the floating link
          global.login_modal.hide_register_modal();
          global.login_modal.show_success_modal(data.username);
          global.login_modal.clear_sign_up_form();
          setTimeout(() => {
            global.login_modal.load_first_registration_step();
          }, 400);
        } else {
          global.notice.message(global.connection._language._active_language.could_not_register_user.replace("%USERNAME%", username), 8000, 1);
          global.login_modal.hide_register_loading_cover();
        }
      }
    }

    if (handle == "user_registered_by_email") {
      if (data) {
        if (data.status == "success" && data.email) {
          console.log(data);
          global.login_modal.load_last_registration_step(data.email);
        }
      } else {
        // Todo: handle this?
        global.login_modal.hide_register_loading_cover();
      }
    }

    if (handle == "user_login_failed") {
      global.login_modal.enable_login_button();
      return;
    }

    if (handle == "user_logged_in") {
      if (data) {
        if (data.status == "success") {
          // Successfully logged in

          if (global.login_modal.modal_visible() == true) {
            global.signal_toggle_login_modal();
          }
          global.right_menu.set_button_text_to_logout();
          global.left_menu.set_logo_block_to_logo();
          if (global.solver && global.solver._tsumego && (data.user_rating < global.solver._tsumego._rating < 150 || data.user_rating > global.solver._tsumego._rating + 150)) {
            const cleanURL = window.location.origin + window.location.pathname;
            window.history.replaceState({}, "", cleanURL);
          }
          loading_cover.reshow(9, "Updating data");

          global.player._user_history = [];
          global.player._user_favorites = [];
          global.login_modal.hide_floating_register_link();

          cookie_handler.update_data("verified_user", data.user_name);
          cookie_handler.update_data("verified_admin", data.admin);
          cookie_handler.update_data("verified_rating", data.user_rating);
          cookie_handler.update_data("verified_id", data.user_id);
          cookie_handler.update_data("verified_avatar", data.user_avatar);
          cookie_handler.update_data("verified_color", data.user_color);
          cookie_handler.update_data("expansion_pack", data.expansion_pack);
          cookie_handler.update_data("session_key", data.session_key);
          cookie_handler.update_data("correct_count", data.correct_count);
          cookie_handler.update_data("wrong_count", data.wrong_count);
          cookie_handler.update_data("max_rating", data.max_rating);
          cookie_handler.update_data("max_time", data.max_time);
          cookie_handler.update_data("min_rating", data.min_rating);
          cookie_handler.update_data("min_time", data.min_time);
          cookie_handler.unset_data("visitor_rating");
          cookie_handler.unset_data("visitor_id");
          cookie_handler.unset_data("visitor_history");
          cookie_handler.unset_data("visitor_favorites");
          cookie_handler.unset_data("statistics");
          // cookie_handler.update_attempted_and_failed_data_from_history(data.history);
          global.player.clear_visitor_id();
          global.player.set_username(data.user_name);
          global.player.set_rating(data.user_rating);
          global.player.set_id(data.user_id);
          global.player.set_avatar(data.user_avatar);
          global.player.set_color(data.user_color);
          global.player.set_session_key(data.session_key);
          global.player.set_verified(true);
          if (data["admin"] && data["admin"]  == 1) {
            global.player.set_admin(true);
            global.signal_show_admin_tools();
          } else {
            global.player.set_admin(false);
          }
          global.player.set_expansion_pack(data.expansion_pack);
          if (data.user_statistics) {
            global.player.set_user_statistics_from_object(data.user_statistics);
          }
          global.player.set_correct_and_wrong_counts(data.correct_count, data.wrong_count);
          global.player.set_max_and_min_ratings(data.max_rating, data.max_time, data.min_rating, data.min_time);
          if ((data.commentor || data.commentor == 0) && data.last_comment && global.player.set_commentor_info) {
            global.player.set_commentor_info(data.commentor, data.last_comment);
            if (data.commentor == 1) {
              this.start_poll_based_on_timestamp(data.last_comment);
            }
          }
          global.signal_user_logged_in();
          this.load_tsumego_list(); // Get new list from server
        } else if (data.status == "not_verified") {
          // User has not yet verified their account
          global.notice.message(global.connection._language._active_language.verify_not_activated, 10000, 1);
        }
        // console.log(data);
      }
    }

    if (handle == "email_availability") {
      if(data && data.status == "success") {
        if(data.available == true) {
          // Todo:
          console.log("Email not in db");
        } else {
          // Todo:
          console.log("Email in db");
        }
      }
    }

    if (handle == "username_availability") {
      if(data && data.status == "success") {
        if(data.available == true) {
          if (data.username && data.username.length > 0) {
            global.login_modal.set_name_icon_to_correct(data.username);
          }
        } else {
          if (data.username && data.username.length > 0) {
            global.login_modal.set_name_icon_to_wrong(data.username);
            global.notice.message(global.connection._language._active_language.username_taken.replace("%USERNAME%", data.username), 3000, 2);
          }
        }
      }
    }

    if (handle == "both_availability") {
      if(data && data.status == "success") {
        if(data.username_available == false || data.email_available == false) {
          if (data.username_available == false) {
            global.notice.message(global.connection._language._active_language.username_taken.replace("%USERNAME%", data.username), 4000, 2);
          } else {
            global.notice.message(global.connection._language._active_language.email_taken, 4000, 1);
          }
          global.login_modal.hide_register_loading_cover();
        } else {
          global.login_modal.load_next_registration_step();
        }
      } else {
        global.notice.message(global.connection._language._active_language.could_not_check_both, 4000, 2);
        global.login_modal.hide_register_loading_cover();
      }
    }

    if (handle == "user_logged_out") {
      if (global.right_menu.visible() == true) {
        global.signal_toggle_side_menu("right");
      }
      global.right_menu.set_button_text_to_login();
      global.left_menu.set_logo_block_to_login();
      // global.notice.message(global.connection._language._active_language.logged_out, 3000, 2);
      global.signal_user_logged_out();
      global.signal_hide_admin_tools();
      global.player.set_admin(false);
      this.stop_poll();
    }

    if (handle == "session_key_check_failed") {
      if (global.solver) {
        global.solver._user_icon.update_info_container_text();
        global.solver._user_icon.update_statistics_container();
      }
      this.load_tsumego_list();
    }

    if (handle == "session_key_checked") {
      if (data) {
        // console.log(data);
        if (data["status"] == "success") {
          if (data.user_rating && data.user_rating != global.player.get_rating()) {
            global.player.update_rating_from_rating_response(data.user_rating);
          }
          if (data.user_statistics) {
            global.player.set_user_statistics_from_object(data.user_statistics);
          }
          if (Object.prototype.hasOwnProperty.call(data, "expansion")) {
            global.player.set_expansion_pack(data.expansion);
          }
          if (data["admin"] && data["admin"] == 1) {
            global.signal_show_admin_tools();
            global.player.set_admin(true);
          } else {
            global.player.set_admin(false);
          }
          if ((data.avatar || data.avatar == 0) && (data.color || data.color == 0)) {
            cookie_handler.update_data("verified_avatar", data.avatar);
            cookie_handler.update_data("verified_color", data.color);
            global.player.set_avatar(data.avatar);
            global.player.set_color(data.color);
            if (global.solver) {
              global.update_top_menu_user_text();
              global.solver._user_icon.populate_info_container();
              global.solver._user_icon.update_statistics_container();
            }
          }
          global.player.set_correct_and_wrong_counts(data.correct_count, data.wrong_count);
          global.player.set_max_and_min_ratings(data.max_rating, data.max_time, data.min_rating, data.min_time);
          cookie_handler.update_data("correct_count", data.correct_count);
          cookie_handler.update_data("wrong_count", data.wrong_count);
          cookie_handler.update_data("max_rating", data.max_rating);
          cookie_handler.update_data("max_time", data.max_time);
          cookie_handler.update_data("min_rating", data.min_rating);
          cookie_handler.update_data("min_time", data.min_time);
          if ((data.commentor || data.commentor == 0) && data.last_comment && global.player.set_commentor_info) {
            global.player.set_commentor_info(data.commentor, data.last_comment);
            if (data.commentor == 1) {
              this.start_poll_based_on_timestamp(data.last_comment);
            }
          }
          // console.log("Session key", global.player._session_key, "validated");
        }
      }
      if (global.solver) {
        global.solver._user_icon.update_info_container_text();
        global.solver._user_icon.update_statistics_container();
      }
      this.load_tsumego_list();
    }

    if (handle == "new_password_requested") {
      global.login_modal.hide_reset_loading_cover();
      global.login_modal.clear_reset_email_field();
      if (data && data.status == "success" && data.email && data.key) {
        global.login_modal.reset_modal_step_forward(data.email, data.key);
      } else {
        global.notice.message(global.connection._language._active_language.could_not_request_password_change, 5000, 1);
      }
    }

    if (handle == "reset_code_verified") {
      if (data && data.status) {
        if (data.status == "success") {
          global.login_modal.hide_reset_loading_cover();
          global.login_modal.reset_modal_step_forward();
          global.login_modal.clear_reset_code_inputs();
        } else if (data.status == "wrong_code") {
          global.notice.message(global.connection._language._active_language.wrong_code, 3000, 1);
          global.login_modal.hide_reset_loading_cover();
        } else if (data.status == "too_many_attempts") {
          global.notice.message(global.connection._language._active_language.too_many_attempts, 3000, 1);
          global.login_modal.hide_reset_loading_cover();
        }
      }
    }

    if (handle == "password_updated") {
      if (data && data.status && data.status == "success") {
        global.notice.message(global.connection._language._active_language.select_password_success, 5000, 1);
        global.login_modal.hide_reset_loading_cover();
        global.login_modal.clear_reset_modal_password_fields();
        global.hide_all_modals();
        global.hide_modal_cover();
      } else {
        global.notice.message(global.connection._language._active_language.select_password_fail, 5000, 1);
        global.login_modal.hide_reset_loading_cover();
      }
    }

    if (handle == "comments_loaded") {
      if (data && data.status && data.status == "success") {
        global.solver._comments.update_comments_data(data);
      }
    }

    if (handle == "discussion_loaded") {
      if (data && data.status && data.status == "success") {
        for (let i = 0; i < data.discussion.length; ++i) {
          if ("original_to_play" in data.discussion[i] && "original_viewport_size" in data.discussion[i]) {
            if (data.discussion[i].original_to_play == "W" && data.discussion[i].tsumego_hash) {
              if (global.solver._tsumego.invert_position_colors && global.solver._tsumego.get_hash_from_position) {
                let tsumego_position = global.solver._tsumego.position_from_hash(data.discussion[i].tsumego_hash, data.discussion[i].original_viewport_size);
                global.solver._tsumego.invert_position_colors(tsumego_position);
                let inverted_hash = global.solver._tsumego.get_hash_from_position(tsumego_position, data.discussion[i].original_viewport_size);
                if (inverted_hash) {
                  data.discussion[i].tsumego_hash = inverted_hash;
                }
              }
            }
          }
        }
        setTimeout(() => {
          global.solver._comments.update_discussion_data(data);
        }, 500);
        if (global.left_menu.remove_notification_box) {
          global.left_menu.remove_notification_box();
        }
      }
    }

    if (handle == "notifications_loaded") {
      if (data && data.status && data.status == "success") {
        this.poll_callback(data.poll_id);
        if (data.count > 0) {
          if (global.top_menu.add_notification_dot) {
            if (data.updated > global.top_menu.get_last_notification_time()) {
              global.top_menu.add_notification_dot(data.updated);
            }
          }
          if (global.left_menu.add_notification_box) {
            global.left_menu.add_notification_box(data.count);
          }
        }
      }
    }

    if (handle == "notifications_failed") {
      this.poll_callback(data.poll_id);
    }

    if (handle == "password_changed") {
      if (data) {
        global.notice.message(global.connection._language._active_language.select_password_success, 5000, 1);
        // console.log(data);
      }
    }

    if (handle == "comment_liked") {
      if (data) {
        // Successfully liked
        if (data["comment_id"] && data["comment_id"].length == 6) {
          for (var i = 0; i < global.solver._comments._last_loaded_data.comments.length; ++i) {
            if (global.solver._comments._last_loaded_data.comments[i].comment_id == data["comment_id"]) {
              global.solver._comments._last_loaded_data.comments[i].liked += 1;
              var like_text = document.getElementById(data["comment_id"] + "-popularity");
              if (like_text) {
                like_text.textContent = global.solver._comments._last_loaded_data.comments[i].liked;
              }
              break;
            }
          }
        }
      }
    }

    if (handle == "comment_disliked") {
      if (data) {
        // Successfully disliked
        if (data["comment_id"] && data["comment_id"].length == 6) {
          for (var i = 0; i < global.solver._comments._last_loaded_data.comments.length; ++i) {
            if (global.solver._comments._last_loaded_data.comments[i].comment_id == data["comment_id"]) {
              global.solver._comments._last_loaded_data.comments[i].liked -= 1;
              var like_text = document.getElementById(data["comment_id"] + "-popularity");
              if (like_text) {
                like_text.textContent = global.solver._comments._last_loaded_data.comments[i].liked;
              }
              break;
            }
          }
        }
      }
    }

    if (handle == "comment_posted") {
      if (data) {
        // Successful post
        global.solver._comments.update_comments_data(data);
        global.notice.message(global.connection._language._active_language.comment_posted, 2500, 3);
        // Update numbers in comment mini-icon and _tsumego object:
        if (data.comments.length) {
          if (global.solver && global.solver._tsumego) {
            global.solver._tsumego._comments = data.comments.length;
          }
          var comments_count_container = document.getElementById("btp-tsumego-comment-count-container");
          if (comments_count_container) {
            comments_count_container.textContent = data.comments.length;
          } else {
            global.solver._mini_icons.activate();
          }
        }
        // Update commentor info
        if (data.timestamp) {
          if (global.player.set_commentor_info) {
            global.player.set_commentor_info(1, data.timestamp);
          }
          if (this._poll_interval > 120000) { // Restart poll only if current interval is too infrequent
            let now = new Date();
            this.start_poll_based_on_timestamp(now.toISOString());
          }
        }
      }
    }

    if (handle == "comment_deleted") {
      if (data) {
        var previous_data = global.solver._comments._last_loaded_data;
        for (const id_to_remove of data["deleted_comments"]) {
          for (var i = 0; i < previous_data.comments.length; ++i) {
            if (previous_data.comments[i].comment_id == id_to_remove) {
              previous_data.comments.splice(i, 1);
            }
          }
        }
        global.solver._comments.update_comments_data(previous_data);
        global.notice.message(global.connection._language._active_language.comment_deleted, 2500, 3);
        if (previous_data.comments.length) {
          if (global.solver && global.solver._tsumego) {
            global.solver._tsumego._comments = previous_data.comments.length;
          }
          var comments_count_container = document.getElementById("btp-tsumego-comment-count-container");
          if (comments_count_container) {
            comments_count_container.textContent = previous_data.comments.length;
          } else {
            global.solver._mini_icons.activate();
          }
        } else {
          var comments_count_container = document.getElementById("btp-tsumego-comment-count-container");
          if (comments_count_container) {
            document.getElementById("btp-tsumego-mini-icon-comment").removeChild(comments_count_container);
          }
        }
      }
    }

    if (handle == "avatar_updated") {
      if (data && data.status && data.status == "success") {
        global.player.set_avatar(data.avatar);
        global.player.set_color(data.color);
        global.top_menu.update_user_icon();
        global.solver._user_icon.update_right_menu_user_icon();
        global.solver._comments.update_user_avatar_and_color(data.avatar, data.color);
      }
    }

    if (handle == "user_rating_updated") {
      if (data && data.status && data.status == "success") {
        data.rating = Number(data.rating);
        global.player.set_rating(data.rating);
        global.player.set_max_and_min_ratings(data.max_rating, data.max_time, data.min_rating, data.min_time);
        cookie_handler.update_data("verified_rating", data.rating);
        const r_text = document.getElementById("btp-tsumego-user-icon-rank-text");
        if (r_text) {
          r_text.textContent = "" + this._language._active_language.get_rank(data.rating) + " (" + data.rating + ")";
        }
        if(global.solver._next_button.active == false) {
          global.solver._next_button.toggle();
        }
        global.update_top_menu_user_text();
        const rank_selector = document.getElementById("right-menu-visitor-rating-selector");
        if (global.solver._user_icon._settings_container_active && rank_selector && rank_selector[rank_selector.selectedIndex].value == data.rating) {
          global.solver._user_icon.hide_settings_container();
        }
        global.solver._user_icon.update_info_container_text();
      }
    }

    if (handle == "tsumego_rating_updated") {
      if (data && data.status && data.status == "success") {
        global.notice.message("Tsumego rating updated", 3000, 1);
        document.getElementById("btp-admin-rating-modal-button").active = true;
        document.getElementById("btp-admin-rating-modal-button").classList.remove("admin-rating-modal-button-inactive");
        // console.log(data);
        if (data.tsumego_id && data.tsumego_id == global.solver._tsumego._id) {
          if (!isNaN(data.rating)) {
            global.solver._tsumego._rating = data.rating;
            global.solver._info.update(global.solver._tsumego, global.solver._go.get_prisoners());
            global.signal_hide_admin_rating_modal();
          }
        }
      }
    }

    if (handle == "payment_intent_created") {
      if (data && data.status && data.status == "success" && data.client_secret && data.mode) {
        if (data.mode == "registration") {
          document.getElementById("btp-register-modal-payment-spinner-container").style.display = "flex";
          document.getElementById("btp-register-modal-payment-spinner-container").style.visibility = "visible";
          document.getElementById("btp-register-modal-payment-spinner-container").style.opacity = 1;
          global.payment.destroy_latest_element("registration");
          global.login_modal.hide_register_loading_cover();
        }
        global.payment.load_payment_block(data.mode, data.client_secret);
      } else if (mode == "registration") {
        global.login_modal.hide_register_loading_cover();
      }
    }

  },


  load_daily_info: function(optional_parameter) {
    var current_time = new Date();
    var month = current_time.getMonth();
    var day = current_time.getDate();
    $.ajax({
      url: "php/load_daily_info.php",
      type: "post",
      dataType: "json",
      data: {
        "day": day,
        "month": month
      },
      complete: function(response) {
        if(response.responseText.includes("error:")) {
          global.notice.message(global.connection._language._active_language.could_not_get_daily_info, 2000, 2);
          return;
        } else {
          if (optional_parameter == "daily_from_url") {
            response.responseJSON.from_url_path = true;
          }
          global.connection.ajax_callback("daily_info_loaded", response.responseJSON);
        }
      },
      error: function() {
        global.notice.message(global.connection._language._active_language.could_not_get_daily_info, 2000, 2);
        return;
      },
    });
  },


  load_daily_tsumego: function(tsumego_id, discussion_item) {
    $.ajax({
      url: "php/load_daily_tsumego.php",
      type: "post",
      dataType: "json",
      data: {
        "tsumego_id": tsumego_id,
      },
      complete: function(response) {
        if(response.responseText.includes("error:")) {
          global.notice.message(global.connection._language._active_language.could_not_load_daily_tsumego, 2000, 1);
          return;
        } else {
          var category_string = response.responseJSON.categories;
          var categories = [];
          for(var i = 0; i < category_string.length; ++i) {
            var index = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".indexOf(category_string[i]);
            categories.push(STATIC_CATEGORIES[index]);
          }
          response.responseJSON.categories = categories;
          var tag_string = response.responseJSON.tags;
          var tags = [];
          for(var i = 0; i < tag_string.length; i += 2) {
            var tag = tag_string.substring(i, i + 2);
            var index = "abcdefghijklmnopqrstuvwxyz".indexOf(tag[1]) + ("ABCDEFGHIJKLMNOPQRSTUVWXYZ".indexOf(tag[0]) * 26)
            tags.push(STATIC_TAGS[index])
          }
          response.responseJSON.tags = tags;
          response.responseJSON.raw = response.responseText;
          if (discussion_item && discussion_item.reference && String(discussion_item.reference) == discussion_item.reference && discussion_item.reference.length == 6) {
            response.responseJSON.discussion_item = discussion_item;
          }
          global.connection.ajax_callback("daily_tsumego_loaded", response.responseJSON);
        }
      },
      error: function() {
        global.notice.message(global.connection._language._active_language.could_not_load_daily_tsumego, 2000, 1);
        return;
      },
    });
  },

  register_user_by_email: function(email, username, password, rating, country, collection, visitor_id) {
    $.ajax({
      url: "php/register_user_by_email.php",
      type: "post",
      dataType: "json",
      data: {
        "email": email,
        "username": username,
        "password": password,
        "rating": rating,
        "country": country,
        "collection": collection,
        "visitor_id": visitor_id
      },
      complete: function(response) {
        if(response.responseText.includes("error:")) {
          if (response.responseText.includes("email already in db")) {
            global.notice.message(global.connection._language._active_language.email_taken, 8000, 1);
          } else if (response.responseText.includes("username already in db")) {
            global.notice.message(global.connection._language._active_language.username_taken.replace("%USERNAME%", username), 8000, 1);
          } else {
            global.notice.message(global.connection._language._active_language.could_not_register_user.replace("%USERNAME%", username), 10000, 1);
          }
          global.login_modal.hide_register_loading_cover();
          return;
        } else {
          global.connection.ajax_callback("user_registered_by_email", response.responseJSON);
        }
      },
      error: function() {
        global.notice.message(global.connection._language._active_language.could_not_register_user.replace("%USERNAME%", username), 10000, 1);
        global.login_modal.hide_register_loading_cover();
        return;
      },
    });
  },

  verify_code: function(email, username, verification_code, visitor_id, currency) {
    $.ajax({
      url: "php/verify_code.php",
      type: "post",
      dataType: "json",
      data: {
        "email": email,
        "username": username,
        "verification_code": verification_code,
        "visitor_id": visitor_id,
        "currency": currency 
      },
      complete: function(response) {
        if (response.responseText.includes("error:")) {
          global.notice.message(global.connection._language._active_language.could_not_verify_code, 4000, 1);
          global.login_modal.hide_register_loading_cover();
          return;
        } else {
          global.connection.ajax_callback("code_verified", response.responseJSON);
        }
      },
      error: function() {
        global.notice.message(global.connection._language._active_language.could_not_verify_code, 4000, 1);
        global.login_modal.hide_register_loading_cover();
        return;
      },
    });
  },

  skip_payment: function(email, username, visitor_id) {
    $.ajax({
      url: "php/skip_payment.php",
      type: "post",
      dataType: "json",
      data: {
        "email": email,
        "username": username,
        "visitor_id": visitor_id,
      },
      complete: function(response) {
        if (response.responseText.includes("error:")) {
          global.notice.message(global.connection._language._active_language.could_not_register_user.replace("%USERNAME%", username), 8000, 1);
          global.login_modal.hide_register_loading_cover();
          return;
        } else {
          global.connection.ajax_callback("payment_skipped", response.responseJSON);
        }
      },
      error: function() {
        global.notice.message(global.connection._language._active_language.could_not_register_user.replace("%USERNAME%", username), 8000, 1);
        global.login_modal.hide_register_loading_cover();
        return;
      },
    });
  },

  login: function(user, password, visitor_id) { // parameter 'user' can be either username or email
    $.ajax({
      url: "php/login.php",
      type: "post",
      dataType: "json",
      data: {"user": user, "password": password, "visitor_id": visitor_id},
      complete: function(response) {
        if(response.responseText.includes("error:")) {
          global.notice.message(global.connection._language._active_language.could_not_log_in, 7000, 1);
          global.connection.ajax_callback("user_login_failed", null);
          return;
        } else {
          // Todo: Validate response data
          global.connection.ajax_callback("user_logged_in", response.responseJSON);
        }
      },
      error: function() {
        global.notice.message(global.connection._language._active_language.could_not_log_in, 7000, 1);
        global.connection.ajax_callback("user_login_failed", null);
        return;
      },
    });
  },

  email_available: function(email) {
    $.ajax({
      url: "php/email_available.php",
      type: "post",
      dataType: "json",
      data: {"email": email},
      complete: function(response) {
        if(response.responseText.includes("error:")) {
          global.notice.message(global.connection._language._active_language.could_not_check_email, 4000, 2);
        } else {
          global.connection.ajax_callback("email_availability", response.responseJSON);
        }
      },
      error: function() {
        global.notice.message(global.connection._language._active_language.could_not_check_email, 4000, 2);
      },
    });
  },

  username_available: function(username, visitor_id) {
    $.ajax({
      url: "php/username_available.php",
      type: "post",
      dataType: "json",
      data: {
        "username": username,
        "visitor_id": visitor_id,
      },
      complete: function(response) {
        if(response.responseText.includes("error:")) {
          global.notice.message(global.connection._language._active_language.could_not_check_username, 4000, 2);
          return;
        } else {
          response.responseJSON["username"] = username;
          global.connection.ajax_callback("username_availability", response.responseJSON);
        }
      },
      error: function() {
        global.notice.message(global.connection._language._active_language.could_not_check_username, 4000, 2);
        return;
      },
    });
  },


  both_available: function(username, email, visitor_id) {
    $.ajax({
      url: "php/both_available.php",
      type: "post",
      dataType: "json",
      data: {
        "username": username,
        "email": email,
        "visitor_id": visitor_id,
      },
      complete: function(response) {
        if(response.responseText.includes("error:")) {
          global.notice.message(global.connection._language._active_language.could_not_check_both, 4000, 2);
          global.login_modal.hide_register_loading_cover();
          return;
        } else {
          global.connection.ajax_callback("both_availability", response.responseJSON);
        }
      },
      error: function() {
        global.notice.message(global.connection._language._active_language.could_not_check_both, 4000, 2);
        global.login_modal.hide_register_loading_cover();
        return;
      },
    });
  },

  logout: function(session_key) {
    $.ajax({
      url: "php/user/logout.php",
      type: "post",
      dataType: "json",
      data: {"session_key": session_key},
      complete: function(response) {
        if(response.responseText.includes("error:")) {
          if (response.responseText.includes("SESSION_KEY")) {
            // global.connection.ajax_callback("user_logged_out", response.responseText);
	          global.connection.session_key_callback(response.responseText);
          } else {
            global.notice.message(global.connection._language._active_language.could_not_log_out, 4000, 1);
          }
        } else {
          global.connection.ajax_callback("user_logged_out", response.responseJSON);
        }
      },
      error: function() {
        global.notice.message(global.connection._language._active_language.could_not_log_out, 4000, 1);
      },
    });
  },

  forgotten_password: function(email) {
    $.ajax({
      url: "php/forgotten_password.php",
      type: "post",
      dataType: "json",
      data: {"email": email},
      complete: function(response) {
        if(response.responseText.includes("error:") || response.responseJSON.status != "success") {
          global.notice.message(global.connection._language._active_language.could_not_request_password_change, 5000, 1);
          global.login_modal.hide_reset_loading_cover();
          return;
        } else {
          global.connection.ajax_callback("new_password_requested", response.responseJSON);
        }
      },
      error: function() {
        global.notice.message(global.connection._language._active_language.could_not_request_password_change, 5000, 1);
        global.login_modal.hide_reset_loading_cover();
        return;
      },
    });
  },

  verify_password_reset_code: function(verification_key, verification_code) {
    $.ajax({
      url: "php/verify_reset_code.php",
      type: "post",
      dataType: "json",
      data: {
        "verification_key": verification_key,
        "verification_code": verification_code,
      },
      complete: function(response) {
        if (response.responseText.includes("error:")) {
          global.notice.message(global.connection._language._active_language.could_not_verify_code, 4000, 1);
          global.login_modal.hide_reset_loading_cover();
          return;
        } else {
          global.connection.ajax_callback("reset_code_verified", response.responseJSON);
        }
      },
      error: function() {
        global.notice.message(global.connection._language._active_language.could_not_verify_code, 4000, 1);
        global.login_modal.hide_reset_loading_cover();
        return;
      },
    });
  },

  update_password: function(verification_key, verification_code, password) {
    $.ajax({
      url: "php/update_password.php",
      type: "post",
      dataType: "json",
      data: {
        "verification_key": verification_key,
        "verification_code": verification_code,
        "password": password,
      },
      complete: function(response) {
        if (response.responseText.includes("error:")) {
          global.notice.message(global.connection._language._active_language.select_password_fail, 4000, 1);
          global.login_modal.hide_reset_loading_cover();
          return;
        } else {
          global.connection.ajax_callback("password_updated", response.responseJSON);
        }
      },
      error: function() {
        global.notice.message(global.connection._language._active_language.select_password_fail, 4000, 1);
        global.login_modal.hide_reset_loading_cover();
        return;
      },
    });
  },

  load_comments: function (tsumego_id, discussion_item, retries = 5) {
    $.ajax({
      url: "php/load_comments.php",
      type: "post",
      dataType: "json",
      data: {
        "tsumego_id": tsumego_id,
      },
      complete: function(response) {
        if(response.responseText.includes("error:")) {
          // Todo: Handle this:
          var message = global.connection._language._active_language.could_not_fetch_comment.replace("%ID%", tsumego_id);
          global.notice.message(message, 2000, 1);
          console.log(response.responseText);
          global.solver._comments.unset_loaded_id();
        } else {
          response.responseJSON["tsumego_id"] = tsumego_id;
          if (discussion_item && discussion_item.reference && String(discussion_item.reference) == discussion_item.reference && discussion_item.reference.length == 6) {
            response.responseJSON.discussion_item = discussion_item;
          }
          global.connection.ajax_callback("comments_loaded", response.responseJSON);
        }
      },
      error: function() {
        if (retries > 0) {
          retries--;
          setTimeout(() => {
            global.connection.load_comments(tsumego_id, discussion_item, retries);
          }, 200);
        } else {
          // Todo: Handle this
          var message = global.connection._language._active_language.could_not_fetch_comment.replace("%ID%", tsumego_id);
          global.notice.message(message, 2000, 1);
          global.solver._comments.unset_loaded_id();
        }
      },
    });
  },

  load_discussion: function (retries = 5) {
    if (global.player.get_expansion_pack() == true) {
      var request_message = "all";
    } else {
      var request_message = "base";
    }
    var current_time = new Date();
    var month = current_time.getMonth();
    var day = current_time.getDate();
    let session_key = "-";
    if (global.player.get_verified() && global.player.get_session_key()) {
      session_key = global.player.get_session_key();
    }
    $.ajax({
      url: "php/load_discussion.php",
      type: "post",
      dataType: "json",
      data: {
        "request": request_message,
        "day": day,
        "month": month,
        "session_key": session_key,
      },
      complete: function(response) {
        if(response.responseText.includes("error:")) {
          global.notice.message(global.connection._language._active_language.could_not_fetch_discussion, 3000, 1);
          return;
        } else {
          global.connection.ajax_callback("discussion_loaded", response.responseJSON);
        }
      },
      error: function() {
        if (retries > 0) {
          retries--;
          setTimeout(() => {
            global.connection.load_discussion(retries);
          }, 200);
        } else {
          global.notice.message(global.connection._language._active_language.could_not_fetch_discussion, 3000, 1);
          return;
        }
      },
    });
  },

  load_notifications: function(poll_id, retries = 5) {
    if (!poll_id || poll_id == "-" || poll_id.length < 16 || poll_id != this._current_poll_id) {
      return;
    }
    let session_key = "-";
    if (global.player.get_verified() && global.player.get_session_key() && global.player.get_session_key().length == 24) {
      session_key = global.player.get_session_key();
    } else {
      return;
    }
    $.ajax({
      url: "php/user/load_notifications.php",
      type: "post",
      dataType: "json",
      data: {
        "session_key": session_key,
      },
      complete: function(response) {
        if(response.responseText.includes("error:")) {
          global.connection.ajax_callback("notifications_failed", {"poll_id": poll_id});
        } else {
          response.responseJSON.poll_id = poll_id;
          global.connection.ajax_callback("notifications_loaded", response.responseJSON);
        }
      },
      error: function() {
        if (retries > 0) {
          retries--;
          setTimeout(() => {
            global.connection.load_notifications(poll_id, retries);
          }, 200);
        } else {
          global.connection.ajax_callback("notifications_failed", {"poll_id": poll_id});
        }
      },
    });
  },

  check_session_key: function(session_key) {
    $.ajax({
      url: "php/user/check_key.php",
      type: "post",
      dataType: "json",
      data: {"session_key": session_key},
      complete: function(response) {
        if(response.responseText.includes("error:") || response.responseJSON.status != "success") {
	        if (response.responseText.includes("SESSION_KEY")) {
	          global.connection.session_key_callback(response.responseText);
          } else {
            global.notice.message(global.connection._language._active_language.could_not_connect_to_server, 4000, 1);
	          global.connection.ajax_callback("session_key_check_failed", null);
          }
          return;
        } else {
	        global.connection.ajax_callback("session_key_checked", response.responseJSON);
        }
      },
      error: function() {
        global.notice.message(global.connection._language._active_language.could_not_connect_to_server, 4000, 1);
	      global.connection.ajax_callback("session_key_check_failed", null);
        return;
      },
    });
  },

  change_password: function(session_key, old_password, new_password) {
    $.ajax({
      url: "php/user/change_password.php",
      type: "post",
      dataType: "json",
      data: {"session_key": session_key, "old_password": old_password, "new_password": new_password},
      complete: function(response) {
        if(response.responseText.includes("error:") || response.responseJSON.status != "success") {
	        if (response.responseText.includes("SESSION_KEY")) {
	          global.connection.session_key_callback(response.responseText);
          } else {
            global.notice.message(global.connection._language._active_language.select_password_fail, 4000, 1);
          }
        } else {
          global.connection.ajax_callback("password_changed", response.responseJSON);
        }
      },
      error: function() {
        global.notice.message(global.connection._language._active_language.select_password_fail, 4000, 1);
      },
    });
  },

  load_tsumego_list: function() {
    if (global.player.get_verified()) {
      this.load_user_tsumego_list();
    } else {
      this.load_public_tsumego_list();
    }
  },

  load_user_tsumego_list: function() {
    if (!global.player.get_session_key()) return;
    $.ajax({
      url: "php/user/load_list.php",
      type: "post",
      dataType: "json",
      data: {"session_key": global.player.get_session_key()},
      complete: function(response) {
        if(response.responseText.includes("error:") || !response.responseJSON.status || response.responseJSON.status != "success") {
          if (response.responseText.includes("SESSION_KEY")) {
            // global.connection.ajax_callback("user_logged_out", response.responseText);
	          global.connection.session_key_callback(response.responseText);
          } else {
            global.notice.message(global.connection._language._active_language.could_not_fetch_tsumego_list, 4000, 1);
          }
        } else {
          // response.responseJSON.raw = JSON.stringify(response.responseJSON.list);
          global.connection.ajax_callback("user_tsumego_list_loaded", response.responseJSON);
        }
      },
      error: function() {
        global.notice.message(global.connection._language._active_language.could_not_fetch_tsumego_list, 4000, 1);
      },
    });
  },

  load_public_tsumego_list: function() {
    $.ajax({
      url: "php/public/load_list.php",
      type: "post",
      dataType: "json",
      data: {"tsumego_request": "all_available"},
      complete: function(response) {
        if(response.responseText.includes("error:") || !response.responseJSON.status || response.responseJSON.status != "success") {
          global.notice.message(global.connection._language._active_language.could_not_fetch_tsumego_list, 4000, 1);
        } else {
          // response.responseJSON.raw = JSON.stringify(response.responseJSON.list);
          global.connection.ajax_callback("public_tsumego_list_loaded", response.responseJSON);
        }
      },
      error: function() {
        global.notice.message(global.connection._language._active_language.could_not_fetch_tsumego_list, 4000, 1);
      },
    });
  },

  load_tsumego_data: function(tsumego_id, tsumego_db, discussion_item) {
    if (global.player.get_verified()) {
      this.load_user_tsumego_data(tsumego_id, tsumego_db, discussion_item);
    } else {
      this.load_public_tsumego_data(tsumego_id, discussion_item, tsumego_db);
    }
  },

  load_user_tsumego_data: function (tsumego_id, tsumego_db, discussion_item, retries = 5) {
    if (!global.player.get_session_key()) return;
    let id_for_comments = "";
    if (discussion_item && discussion_item.tsumego_id && discussion_item.tsumego_id.length == 6) {
      id_for_comments = discussion_item.tsumego_id;
    }
    $.ajax({
      url: "php/user/load_data.php",
      type: "post",
      dataType: "json",
      data: {"id": tsumego_id, "db": tsumego_db, "session_key": global.player.get_session_key(), "c_id": id_for_comments},
      complete: function(response) {
        if(response.responseText.includes("error:")) {
	        if (response.responseText.includes("SESSION_KEY")) {
	          global.connection.session_key_callback(response.responseText);
          } else {
            // TODO: Handle if tsumego has been removed, un-published or set to inactive?
            global.notice.message(global.connection._language._active_language.could_not_fetch_tsumego_data, 4000, 1);
            let data = {};
            if (discussion_item && discussion_item.reference && String(discussion_item.reference) == discussion_item.reference && discussion_item.reference.length == 6) {
              data.discussion_item = discussion_item;
            }
            global.connection.ajax_callback("tsumego_loading_failed", data);
            return;
          }
        } else {
          // Todo: Validate response data
          var category_string = response.responseJSON.categories;
          var categories = [];
          for(var i = 0; i < category_string.length; ++i) {
            var index = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".indexOf(category_string[i]);
            categories.push(STATIC_CATEGORIES[index]);
          }
          response.responseJSON.categories = categories;
          var tag_string = response.responseJSON.tags;
          var tags = [];
          for(var i = 0; i < tag_string.length; i += 2) {
            var tag = tag_string.substring(i, i + 2);
            var index = "abcdefghijklmnopqrstuvwxyz".indexOf(tag[1]) + ("ABCDEFGHIJKLMNOPQRSTUVWXYZ".indexOf(tag[0]) * 26)
            tags.push(STATIC_TAGS[index])
          }
          response.responseJSON.tags = tags;
          response.responseJSON.raw = response.responseText;
          if (discussion_item && discussion_item.reference && String(discussion_item.reference) == discussion_item.reference && discussion_item.reference.length == 6) {
            response.responseJSON.discussion_item = discussion_item;
          }
          global.connection.ajax_callback("tsumego_data_loaded", response.responseJSON);
        }
      },
      error: function() {
        if (retries > 0) {
          retries--;
          setTimeout(() => {
            global.connection.load_user_tsumego_data(tsumego_id, tsumego_db, discussion_item, retries);
          }, 200);
        } else {
          global.notice.message(global.connection._language._active_language.could_not_fetch_tsumego_data, 4000, 1);
          let data = {};
          if (discussion_item && discussion_item.reference && String(discussion_item.reference) == discussion_item.reference && discussion_item.reference.length == 6) {
            data.discussion_item = discussion_item;
          }
          global.connection.ajax_callback("tsumego_loading_failed", data);
          return;
        }
      },
    });
  },


  load_public_tsumego_data: function (tsumego_id, discussion_item, tsumego_db, retries = 5) {
    let id_for_comments = "";
    if (discussion_item && discussion_item.tsumego_id && discussion_item.tsumego_id.length == 6) {
      id_for_comments = discussion_item.tsumego_id;
    }
    $.ajax({
      url: "php/public/load_data.php",
      type: "post",
      dataType: "json",
      data: {
        "id": tsumego_id,
        "vid": global.player._visitor_id,
        "rating": global.player.get_rating(),
        "c_id": id_for_comments,
        "db": tsumego_db
      },
      complete: function(response) {
        if(response.responseText.includes("error:")) {
          // TODO: Handle if tsumego has been removed, un-published or set to inactive?
          global.notice.message(global.connection._language._active_language.could_not_fetch_tsumego_data, 4000, 1);
          let data = {};
          if (discussion_item && discussion_item.reference && String(discussion_item.reference) == discussion_item.reference && discussion_item.reference.length == 6) {
            data.discussion_item = discussion_item;
          }
          global.connection.ajax_callback("tsumego_loading_failed", data);
          return;
        } else {
          // Todo: Validate response data
          var category_string = response.responseJSON.categories;
          var categories = [];
          for(var i = 0; i < category_string.length; ++i) {
            var index = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".indexOf(category_string[i]);
            categories.push(STATIC_CATEGORIES[index]);
          }
          response.responseJSON.categories = categories;
          var tag_string = response.responseJSON.tags;
          var tags = [];
          for(var i = 0; i < tag_string.length; i += 2) {
            var tag = tag_string.substring(i, i + 2);
            var index = "abcdefghijklmnopqrstuvwxyz".indexOf(tag[1]) + ("ABCDEFGHIJKLMNOPQRSTUVWXYZ".indexOf(tag[0]) * 26)
            tags.push(STATIC_TAGS[index])
          }
          response.responseJSON.tags = tags;
          response.responseJSON.raw = response.responseText;
          if (discussion_item && discussion_item.reference && String(discussion_item.reference) == discussion_item.reference && discussion_item.reference.length == 6) {
            response.responseJSON.discussion_item = discussion_item;
          }
          global.connection.ajax_callback("tsumego_data_loaded", response.responseJSON);
        }
      },
      error: function() {
        if (retries > 0) {
          retries--;
          setTimeout(() => {
            global.connection.load_public_tsumego_data(tsumego_id, discussion_item, tsumego_db, retries);
          }, 200);
        } else {
          global.notice.message(global.connection._language._active_language.could_not_fetch_tsumego_data, 4000, 1);
          let data = {};
          if (discussion_item && discussion_item.reference && String(discussion_item.reference) == discussion_item.reference && discussion_item.reference.length == 6) {
            data.discussion_item = discussion_item;
          }
          global.connection.ajax_callback("tsumego_loading_failed", data);
          return;
        }
      },
    });
  },

  get_tsumego_info: function(id_list, offset, nr_to_show, type) {
    if (global.player.get_verified()) {
      this.get_user_tsumego_info(id_list, offset, nr_to_show, type);
    } else {
      this.get_public_tsumego_info(id_list, offset, nr_to_show, type);
    }
  },

  get_user_tsumego_info: function (id_list, offset, nr_to_show, type) {
    if (!global.player.get_session_key()) return;
    $.ajax({
      url: "php/user/get_info.php",
      type: "post",
      dataType: "json",
      data: {
        "id_list": id_list,
        "session_key": global.player.get_session_key()
      },
      complete: function(response) {
        if(response.responseText.includes("error:")) {
          if (response.responseText.includes("SESSION_KEY")) {
	          global.connection.session_key_callback(response.responseText);
          } else {
            console.log(response.responseText);
            console.log("Error fetching additional tsumego info");
          }
          return;
        } else {
          response.responseJSON["offset"] = offset;
          response.responseJSON["nr_to_show"] = nr_to_show;
          response.responseJSON["type"] = type;
          global.connection.ajax_callback("tsumego_info_gotten", response.responseJSON);
        }
      },
      error: function() {
        console.log("Error fetching additional tsumego info");
        return;
      },
    });
  },

  get_public_tsumego_info: function(id_list, offset, nr_to_show, type) {
    $.ajax({
      url: "php/public/get_info.php",
      type: "post",
      dataType: "json",
      data: {"id_list": id_list},
      complete: function(response) {
        if(response.responseText.includes("error:") || !response.responseJSON.status || response.responseJSON.status != "success") {
          // global.notice.message(global.connection._language._active_language.could_not_fetch_tsumego_list, 4000, 1);
        } else {
          response.responseJSON["offset"] = offset;
          response.responseJSON["nr_to_show"] = nr_to_show;
          response.responseJSON["type"] = type;
          global.connection.ajax_callback("tsumego_info_gotten", response.responseJSON);
        }
      },
      error: function() {
        // global.notice.message(global.connection._language._active_language.could_not_fetch_tsumego_list, 4000, 1);
      },
    });
  },

  update_favorites: function (tsumego_id, action) {
    if (global.player.get_verified()) {
      this.update_user_favorites(tsumego_id, action);
    } else {
      // No saving of favorites on the server for visitors
    }
  },

  update_user_favorites: function (tsumego_id, action) {
    // Note: "action" parameter should be "add" or "remove"
    const t_rating = global.solver._tsumego._rating;
    const t_user_id = global.player.get_id();
    const t_tsumego_id = tsumego_id;
    const t_tsumego = global.solver._tsumego;
    $.ajax({
      url: "php/user/update_favorites.php",
      type: "post",
      dataType: "json",
      data: {
        "session_key": global.player.get_session_key(),
        "tsumego_id": tsumego_id,
        "action": action,
      },
      complete: function(response) {
        if(response.responseText.includes("error:")) {
          console.log("Error updating favorites");
          return;
        } else {
          if (response.responseJSON.status && response.responseJSON.status == "success") {
            if (action == "add") {
              global.notice.message(global.connection._language._active_language.favorite_added, 2000, 1);
              global.player.add_item_to_user_favorites(t_rating, response.responseJSON.timestamp, t_user_id, t_tsumego_id, t_tsumego);
            } else if (action == "remove") {
              global.notice.message(global.connection._language._active_language.favorite_removed, 2000, 1);
              global.player.remove_item_from_user_favorites(t_tsumego_id);
            }
          }
        }
      },
      error: function() {
        console.log("Error updating user attempts");
        return;
      },
    });
  },

  check_if_tsumego_is_part_of_expansion: function (tsumego_id) {
    const converted_id = (tsumego_id[0] == "0" ? String(Number(tsumego_id)) : tsumego_id);
    $.ajax({
      url: "php/part_of_expansion.php",
      type: "post",
      dataType: "json",
      data: {
        "tsumego_id": tsumego_id
      },
      complete: function(response) {
        if(response.responseText.includes("error:")) {
          global.notice.message(global.connection._language._active_language.url_tsumego_fail.replace("%TSUMEGO_ID%", converted_id), 4000, 1);
        } else {
          if (response.responseJSON.status && response.responseJSON.status  == "success") {
            global.notice.message(global.connection._language._active_language.url_tsumego_fail_pack.replace("%TSUMEGO_ID%", converted_id), 8000, 1);
          } else {
            global.notice.message(global.connection._language._active_language.url_tsumego_fail.replace("%TSUMEGO_ID%", converted_id), 4000, 1);
          }
        }
      },
      error: function() {
        global.notice.message(global.connection._language._active_language.url_tsumego_fail.replace("%TSUMEGO_ID%", converted_id), 4000, 1);
      },
    });
  },

  update_attempts: function (tsumego_id, tsumego_db) {
    if (global.player.get_verified()) {
      this.update_user_attempts(tsumego_id, tsumego_db);
    } else {
      this.update_public_attempts(tsumego_id);
    }
  },

  update_public_attempts: function (tsumego_id) {
    $.ajax({
      url: "php/public/update_attempts.php",
      type: "post",
      dataType: "json",
      data: {"tsumego_id": tsumego_id, "daily": global.solver._tsumego.get_daily()},
      complete: function(response) {
        if(response.responseText.includes("error:")) {
          console.log("Error updating public attempts");
        } else {
          // console.log("Attempts updated");
        }
      },
      error: function() {
        console.log("Error updating public attempts");
      },
    });
  },

  update_user_attempts: function (tsumego_id, tsumego_db) {
    $.ajax({
      url: "php/user/update_attempts.php",
      type: "post",
      dataType: "json",
      data: {"tsumego_id": tsumego_id, "db": tsumego_db},
      complete: function(response) {
        if(response.responseText.includes("error:")) {
          console.log("Error updating user attempts");
        } else {
          // console.log("Attempts updated");
        }
      },
      error: function() {
        console.log("Error updating user attempts");
      },
    });
  },

  update_correct: function (tsumego_id, tsumego_db, player_rating_diff, player_statistics_diff, diff_reduced) {
    if (global.player.get_verified()) {
      this.update_user_correct(tsumego_id, tsumego_db, player_rating_diff, player_statistics_diff, diff_reduced);
    } else {
      this.update_public_correct(tsumego_id);
    }
  },

  update_public_correct: function (tsumego_id) {
    const constant_tsumego = global.solver._tsumego;
    $.ajax({
      url: "php/public/update_correct.php",
      type: "post",
      dataType: "json",
      data: {"tsumego_id": tsumego_id, "daily": global.solver._tsumego.get_daily()},
      complete: function(response) {
        if(response.responseText.includes("error:")) {
          console.log("Error updating public correct");
        } else {
          // console.log("'correct' updated");
          const rating_before_update = global.player.get_rating();
          const diff_before_update = global.player.get_rating_diff();
          global.player.update_rating_from_rating_diff();
          global.player.update_statistics_from_statistics_diff();
          const now = new Date();
          const timestamp = now.toISOString().split(".")[0].replace("T", " ");
          global.player.add_info_to_user_history(1, rating_before_update, timestamp, tsumego_id, -1, diff_before_update, constant_tsumego);
          if (global.solver) {
            global.solver._user_icon.update_info_container_text();
            global.solver._user_icon.update_statistics_container();
          }
        }
      },
      error: function() {
        console.log("Error updating public correct");
      },
    });
  },

  update_user_correct: function (tsumego_id, tsumego_db, rating_diff, statistics_diff, diff_reduced) {
    if (!global.player.get_session_key()) return;
    const constant_tsumego = global.solver._tsumego;
    // console.log("Rating diff:", rating_diff, "- statistics_diff:", statistics_diff);
    $.ajax({
      url: "php/user/update_correct.php",
      type: "post",
      dataType: "json",
      data: {
        "tsumego_id": tsumego_id,
        "db": tsumego_db,
        "session_key": global.player.get_session_key(),
        "r_diff": rating_diff,
        "s_diff": statistics_diff,
        "rated": global.solver._slide.get_rated(),
        "diff_reduced": diff_reduced,
      },
      complete: function(response) {
        if(response.responseText.includes("error:")) {
          if (response.responseText.includes("SESSION_KEY")) {
            // global.connection.ajax_callback("user_logged_out", response.responseText);
	          global.connection.session_key_callback(response.responseText);
          } else {
            console.log(response.responseText);
            console.log("Error updating user correct");
          }
        } else {
          // console.log("'correct' updated");
          // console.log(response.responseJSON);
          const rating_before_update = global.player.get_rating();
          global.player.update_rating_from_rating_response(response.responseJSON.user_rating);
          global.player.set_user_statistics_from_object(response.responseJSON.user_statistics);
          if (response.responseJSON.correct_count != global.player.get_correct_count() || response.responseJSON.wrong_count != global.player.get_wrong_count()) {
            global.player.set_correct_and_wrong_counts(response.responseJSON.correct_count, response.responseJSON.wrong_count);
          }
          if (response.responseJSON.max_rating > global.player._max_rating || response.responseJSON.min_rating < global.player._min_rating) {
            global.player.set_max_and_min_ratings(response.responseJSON.max_rating, response.responseJSON.max_time, response.responseJSON.min_rating, response.responseJSON.min_time);
          }
          global.player.add_info_to_user_history(1, rating_before_update, response.responseJSON.timestamp, tsumego_id, global.player.get_id(), rating_diff, constant_tsumego);
          if (global.solver) {
            global.solver._user_icon.update_info_container_text();
            global.solver._user_icon.update_statistics_container();
          }
        }
      },
      error: function() {
        console.log("Error updating user correct");
      },
    });
  },

  update_avatar: function (avatar, color) {
    if (!global.player.get_session_key()) return;
    $.ajax({
      url: "php/user/update_avatar.php",
      type: "post",
      dataType: "json",
      data: {
        "session_key": global.player.get_session_key(),
        "avatar": avatar,
        "color": color,
      },
      complete: function(response) {
        if(response.responseText.includes("error:")) {
          if (response.responseText.includes("SESSION_KEY")) {
	          global.connection.session_key_callback(response.responseText);
          } else {
            console.log(response.responseText);
          }
        } else {
          global.connection.ajax_callback("avatar_updated", response.responseJSON);
        }
      },
      error: function() {
        console.log("Error updating user correct");
      },
    });
  },

  update_user_rating: function (rating, retries = 3) {
    if (!global.player.get_session_key()) return;
    $.ajax({
      url: "php/user/update_rating.php",
      type: "post",
      dataType: "json",
      data: {
        "session_key": global.player.get_session_key(),
        "rating": rating,
      },
      complete: function(response) {
        if(response.responseText.includes("error:")) {
          if (response.responseText.includes("SESSION_KEY")) {
	          global.connection.session_key_callback(response.responseText);
          } else {
            global.notice.message(global.connection._language._active_language.could_not_connect_to_server, 3600, 1);
          }
          global.solver._user_icon.hide_settings_loading_cover();
        } else {
          global.connection.ajax_callback("user_rating_updated", response.responseJSON);
        }
      },
      error: function() {
        if (retries > 0) {
          retries--;
          setTimeout(() => {
            global.connection.update_user_rating(rating, retries);
          }, 200);
        } else {
          global.notice.message(global.connection._language._active_language.could_not_connect_to_server, 3600, 1);
          global.solver._user_icon.hide_settings_loading_cover();
        }
      },
    });
  },

  admin_comment_deletion: function(session_key, tsumego_id, db, comment_id) {
    $.ajax({
      url: "php/admin/delete_comment.php",
      type: "post",
      dataType: "json",
      data: {
        "session_key": session_key,
        "tsumego_id": tsumego_id,
        "db": db,
        "comment_id": comment_id,
      },
      complete: function(response) {
        if(response.responseText.includes("error:") || response.responseJSON.status != "success") {
	        if (response.responseText.includes("SESSION_KEY")) {
	          global.connection.session_key_callback(response.responseText);
          } else {
            console.log(response.responseText);
            global.notice.message(global.connection._language._active_language.could_not_connect_to_server, 6000, 1);
          }
        } else {
          if (response.responseJSON.status && response.responseJSON.status == "success") {
	          global.connection.ajax_callback("comment_deleted", response.responseJSON);
          }
        }
      },
      error: function() {
        global.notice.message(global.connection._language._active_language.could_not_connect_to_server, 6000, 1);
      },
    });
  },

  update_tsumego_rating: function (tsumego_id, tsumego_db, rating) {
    if (!global.player.get_session_key()) return;
    $.ajax({
      url: "php/admin/update_rating.php",
      type: "post",
      dataType: "json",
      data: {"session_key": global.player.get_session_key(), "tsumego_id": tsumego_id, "db": tsumego_db, "rating": rating},
      complete: function(response) {
        if(response.responseText.includes("error:")) {
          if (response.responseText.includes("SESSION_KEY")) {
            // global.connection.ajax_callback("user_logged_out", response.responseText);
	          global.connection.session_key_callback(response.responseText);
          } else {
            global.notice.message(response.responseText, 6000, 2);
          }
        } else {
          global.connection.ajax_callback("tsumego_rating_updated", response.responseJSON);
        }
      },
      error: function() {
        console.log("Error updating rating as admin");
      },
    });
  },

  update_wrong: function (tsumego_id, tsumego_db, player_rating_diff, player_statistics_diff, source) {
    if (global.player.get_verified()) {
      this.update_user_wrong(tsumego_id, tsumego_db, player_rating_diff, player_statistics_diff, source);
    } else {
      const constant_tsumego = global.solver._tsumego;
      // No need to update anything on the server in this case.
      const rating_before_update = global.player.get_rating();
      const diff_before_update = global.player.get_rating_diff();
      global.player.update_rating_from_rating_diff();
      global.player.update_statistics_from_statistics_diff();
      if (source == "move") {
        const now = new Date();
        const timestamp = now.toISOString().split(".")[0].replace("T", " ");
        global.player.add_info_to_user_history(0, rating_before_update, timestamp, tsumego_id, -1, diff_before_update, constant_tsumego);
      }
      if (global.solver) {
        global.solver._user_icon.update_info_container_text();
        global.solver._user_icon.update_statistics_container();
      }
    }
  },

  update_user_wrong: function (tsumego_id, tsumego_db, rating_diff, statistics_diff, source) {
    if (!global.player.get_session_key()) return;
    const constant_tsumego = global.solver._tsumego;
    $.ajax({
      url: "php/user/update_wrong.php",
      type: "post",
      dataType: "json",
      data: {
        "tsumego_id": tsumego_id,
        "db": tsumego_db,
        "session_key": global.player.get_session_key(),
        "r_diff": rating_diff,
        "s_diff": statistics_diff,
        "source": source,
        "rated": global.solver._slide.get_rated(),
      },
      complete: function(response) {
        if(response.responseText.includes("error:")) {
          if (response.responseText.includes("SESSION_KEY")) {
            // global.connection.ajax_callback("user_logged_out", response.responseText);
	          global.connection.session_key_callback(response.responseText);
          } else {
            console.log("Error updating user wrong");
            console.log(response.responseText);
          }
        } else {
          // console.log("'wrong' updated");
          const rating_before_update = global.player.get_rating();
          global.player.update_rating_from_rating_response(response.responseJSON.user_rating);
          global.player.set_user_statistics_from_object(response.responseJSON.user_statistics);
          if (response.responseJSON.correct_count != global.player.get_correct_count() || response.responseJSON.wrong_count != global.player.get_wrong_count()) {
            global.player.set_correct_and_wrong_counts(response.responseJSON.correct_count, response.responseJSON.wrong_count);
          }
          if (response.responseJSON.max_rating > global.player._max_rating || response.responseJSON.min_rating < global.player._min_rating) {
            global.player.set_max_and_min_ratings(response.responseJSON.max_rating, response.responseJSON.max_time, response.responseJSON.min_rating, response.responseJSON.min_time);
          }
          global.player.add_info_to_user_history(0, rating_before_update, response.responseJSON.timestamp, tsumego_id, global.player.get_id(), rating_diff, constant_tsumego);
          if (global.solver) {
            global.solver._user_icon.update_info_container_text();
            global.solver._user_icon.update_statistics_container();
          }
        }
      },
      error: function() {
        console.log("Error updating user wrong");
      },
    });
  },

  post_comment: function(session_key, tsumego_id, parent_id, comment, hash, last_move, variation, to_play, ko) {
    // console.log(session_key, tsumego_id, parent_id, comment, hash, last_move, variation, to_play, ko);
    $.ajax({
      url: "php/user/post_comment.php",
      type: "post",
      dataType: "json",
      data: {
        "session_key": session_key,
        "tsumego_id": tsumego_id,
        "parent_id": parent_id,
        "comment": comment,
        "hash": hash,
        "last_move": last_move,
        "variation": variation,
        "to_play": to_play,
        "ko": ko,
      },
      complete: function(response) {
        if(response.responseText.includes("error:") || (response.responseJSON && response.responseJSON.status != "success")) {
          console.log(response.responseText);
	        if (response.responseText.includes("SESSION_KEY")) {
	          global.connection.session_key_callback(response.responseText);
            global.solver._comments.activate_write_field();
          } else {
            console.log(response.responseText);
            global.notice.message(global.connection._language._active_language.could_not_connect_to_server, 6000, 1);
            global.solver._comments.activate_write_field();
          }
        } else {
          if (response.responseJSON && response.responseJSON.status && response.responseJSON.status == "success") {
            response.responseJSON["tsumego_id"] = tsumego_id;
	          global.connection.ajax_callback("comment_posted", response.responseJSON);
          }
        }
      },
      error: function() {
        global.notice.message(global.connection._language._active_language.could_not_connect_to_server, 6000, 1);
        global.solver._comments.activate_write_field();
      },
    });
  },

  delete_comment: function(session_key, tsumego_id, db, comment_id) {
    $.ajax({
      url: "php/user/delete_comment.php",
      type: "post",
      dataType: "json",
      data: {
        "session_key": session_key,
        "tsumego_id": tsumego_id,
        "db": db,
        "comment_id": comment_id,
      },
      complete: function(response) {
        if(response.responseText.includes("error:") || response.responseJSON.status != "success") {
	        if (response.responseText.includes("SESSION_KEY")) {
	          global.connection.session_key_callback(response.responseText);
          } else {
            console.log(response.responseText);
            global.notice.message(global.connection._language._active_language.could_not_connect_to_server, 6000, 1);
          }
        } else {
          if (response.responseJSON.status && response.responseJSON.status == "success") {
	          global.connection.ajax_callback("comment_deleted", response.responseJSON);
          }
        }
      },
      error: function() {
        global.notice.message(global.connection._language._active_language.could_not_connect_to_server, 6000, 1);
      },
    });
  },
  
  update_visitor_likes: function(tsumego_id, comment_id, action) {
    // NOTE: comment_id shall be "-" if the item is a tsumego and not a comment
    //       action must be "like" or "dislike"
    $.ajax({
      url: "php/public/update_likes.php",
      type: "post",
      dataType: "json",
      data: {
        "tsumego_id": tsumego_id,
        "comment_id": comment_id,
        "action": action
      },
      complete: function(response) {
        if(response.responseText.includes("error:") || response.responseJSON.status != "success") {
          console.log(response.responseText);
          // global.notice.message(global.connection._language._active_language.could_not_connect_to_server, 2500, 2);
          return;
        } else {
          if (response.responseJSON.status && response.responseJSON.status == "success") {
            if (comment_id.length == 6) {
              if (action == "like") {
                global.connection.ajax_callback("comment_liked", response.responseJSON);
              } else if (action == "dislike") {
                global.connection.ajax_callback("comment_disliked", response.responseJSON);
              }
            }
          }
        }
      },
      error: function() {
        global.notice.message(global.connection._language._active_language.could_not_connect_to_server, 2500, 2);
        return;
      },
    });
  },

  update_likes: function(session_key, tsumego_id, comment_id, db, action) {
    // NOTE: comment_id shall be "-" if the item is a tsumego and not a comment
    //       db should always be set to tsumego db, even if the item is a comment
    //       action must be "like" or "dislike"
    $.ajax({
      url: "php/user/update_likes.php",
      type: "post",
      dataType: "json",
      data: {
        "session_key": session_key,
        "tsumego_id": tsumego_id,
        "comment_id": comment_id,
        "db": db,
        "action": action
      },
      complete: function(response) {
        if(response.responseText.includes("error:") || response.responseJSON.status != "success") {
	        if (response.responseText.includes("SESSION_KEY")) {
	          global.connection.session_key_callback(response.responseText);
          } else {
            console.log(response.responseText);
            // global.notice.message(global.connection._language._active_language.could_not_connect_to_server, 2500, 2);
          }
        } else {
          if (response.responseJSON.status && response.responseJSON.status == "success") {
            if (comment_id.length == 6) {
              if (action == "like") {
                // Comment liked:
	              global.connection.ajax_callback("comment_liked", response.responseJSON);
              } else if (action == "dislike") {
                // Comment disliked:
	              global.connection.ajax_callback("comment_disliked", response.responseJSON);
              }
            }
          }
        }
      },
      error: function() {
        global.notice.message(global.connection._language._active_language.could_not_connect_to_server, 2500, 2);
      },
    });
  },


  create_payment_intent: function(currency, mode, reference) {
    $.ajax({
      url: "php/payment_intent.php",
      type: "post",
      dataType: "json",
      data: {
        "currency": currency,
        "mode": mode,
        "reference": reference
      },
      complete: function(response) {
        if(response.responseText.includes("error:") || response.responseJSON.status != "success") {
          console.log(response.responseText);
          global.notice.message(global.connection._language._active_language.payment_intent_error, 4000, 1);
          if (mode == "registration") {
            global.login_modal.hide_register_loading_cover();
          }
          return;
        } else {
          if (response.responseJSON.status && response.responseJSON.status == "success") {
	          global.connection.ajax_callback("payment_intent_created", response.responseJSON);
          }
        }
      },
      error: function() {
        global.notice.message(global.connection._language._active_language.payment_intent_error, 4000, 1);
        if (mode == "registration") {
          global.login_modal.hide_register_loading_cover();
        }
        return;
      },
    });
  },

};



