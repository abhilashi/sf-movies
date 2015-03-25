$(document).ready(function () {
    'use strict';

    var DEFAULT_ZOOM = 15;
    var active_markers = [];
    var $window = $(window);

    // Backbone
    var dispatcher = _.clone(Backbone.Events);

    var Location = Backbone.Model.extend({
        initialize: function (obj) {
            this.id = obj.identifier;
            this.marker = new google.maps.Marker({
                position: {lat: obj.lat, lng: obj.lng},
                map: map,
                icon: 'http://chart.apis.google.com/chart?chst=d_map_pin_letter&chld=' + (obj.idx + 1) + '|FE7569'
            });
            this.marker.idx = obj.idx + 1;
        },
        destroy: function () {
            this.marker.setMap(null);
            delete this.marker;
            Backbone.Model.prototype.destroy.apply(this, arguments);
        }
    });

    var LocationList = Backbone.Collection.extend({
        fetchTimeout: null,
        delayedFetch: function () {
            clearTimeout(this.fetchTimeout);
            var that = this;
            this.fetchTimeout = setTimeout(function () {
                that.fetch({
                    reset: true,
                    success: function(){
                        dispatcher.trigger('LocationList:load');
                    }
                });
                that.fetchTimeout = null;
            }, 500);
        },
        model: Location,
        url: function () {
            return '/json/locations?bounds=' + map.getBounds().toUrlValue() + '&center=' + map.getCenter().toUrlValue();
        },
        reset: function () {
            this.each(function (model) {
                if(model && model.hasOwnProperty('destroy')){
                    model.destroy();
                }
            });
            active_markers = [];
            Backbone.Collection.prototype.reset.apply(this, arguments);
        }
    });

    var Locations = new LocationList;

    var LocationView = Backbone.View.extend({
        tagName: 'div',
        template: _.template($('#location-tile').html()),
        events: {
            'click .tile-poster': 'invokeMovieDetails',
            'click': 'updateState'
        },
        initialize: function () {
            this.listenTo(this.model, 'change', this.render);
            this.listenTo(this.model, 'destroy', this.remove);

            this.marker = this.model.marker;
            this.marker.view = this;

            google.maps.event.addListener(this.marker, 'click', this.updateState.bind(this));
            dispatcher.on('ListView:scroll', this.setStreetView, this);
        },
        render: function () {
            var template_data = this.model.toJSON();
            template_data['street_view'] = '/static/img/streetview.png';
            this.$el.html(this.template(template_data));
            return this;
        },
        setStreetView: function(){
            if(this.isInView()){
                // To set street view iage only when scrolled into view
                var sview = 'https://maps.googleapis.com/maps/api/streetview?size=100x100&location=';
                sview += this.marker.getPosition().toUrlValue() + '&sensor=false';
                this.$el.find('img.tile-sview').attr('src', sview);
            }
        },
        isInView: function(){
            var docViewTop = $window.scrollTop();
            var docViewBottom = docViewTop + $window.height();

            var elemTop = this.$el.offset().top;
            var elemBottom = elemTop + this.$el.height();

            return ((elemTop <= docViewBottom) && (elemBottom >= docViewTop));
        },
        className: 'horizontal-tile grey groove',
        updateState: function(){
            if(this.marker.highlighted){
                this.nohighlight();
            } else {
                this.highlight();
            }
        },
        highlight: function(){
            this.marker.setIcon('http://chart.apis.google.com/chart?chst=d_map_pin_letter&chld=' + this.marker.idx + '|55ACEE');
            this.$el.children('.inner-tile').addClass('highlight');
            this.marker.highlighted = true;
            active_markers.push(this.marker);
        },
        nohighlight: function(){
            this.marker.setIcon('http://chart.apis.google.com/chart?chst=d_map_pin_letter&chld=' + this.marker.idx + '|FE7569');
            this.$el.children('.inner-tile').removeClass('highlight');
            this.marker.highlighted = false;
            var idx = [];
            for(var i=0; i<active_markers.length; i++){
                if(active_markers[i] == this.marker){
                    idx.push(i);
                }
            }
            for(i=0; i<idx.length; i++){
                active_markers.splice(idx[i], 1);
            }
        },
        setCenter: function(){
            initializeMap({
                center: this.location,
                zoom: DEFAULT_ZOOM
            });
        },
        invokeMovieDetails: function(ev){
            var movie_id = this.model.toJSON()['movie_id'];
            var movie = new Movie({id: movie_id});
            movie.fetch({
                data: {city: Cities.selectedCity.id},
                success: function(data){
                    var movieView = new MovieView({model: movie});
                    movieView.render();

                    // Purely for highlighting purposes
                    var movieSuggestion = new MovieSuggestion(data.attributes);
                    movieSuggestion.select();
                }
            });
            ev.stopPropagation();
        }
    });

    var LocationListView = Backbone.View.extend({
        el: $('#tiles'),
        list: [],
        initialize: function () {
            this.listenTo(Locations, 'add', this.addOne);
            this.listenTo(Locations, 'reset', this.addAll);
            this.listenTo(Locations, 'all', this.render);
        },
        events: {
            'scroll': 'triggerScroll'
        },
        addOne: function (location) {
            var view = new LocationView({model: location});
            this.$el.append(view.render().el);
            view.setStreetView();
            this.list.push(view);
        },
        addAll: function () {
            this.$el.empty();
            Locations.each(this.addOne, this);
        },
        triggerScroll: function(){
            dispatcher.trigger('ListView:scroll');
        }
    });

    var ListingView = new LocationListView;

    var Movie = Backbone.Model.extend({
        urlRoot: '/json/movie'
    });

    var MovieView = Backbone.View.extend({
        events: {
            'click .back': 'close'
        },
        el: $('#movie-details'),
        template: _.template($('#movie-template').html()),
        render: function(){
            this.$el.html(this.template(this.model.toJSON()));
            this.$el.show();
        },
        close: function(){
            this.$el.empty().hide();
        }
    });

    var MovieSuggestion = Backbone.Model.extend({
        initialize: function(obj){
            this.id = obj.identifier;
            this.bbox = obj.bbox;
            this.locations = obj.locations;
        },
        select: function(){
            var currentBBox = map.getBounds();
            var newNE = new google.maps.LatLng(this.bbox.ne.lat, this.bbox.ne.lng);
            var newSW = new google.maps.LatLng(this.bbox.sw.lat, this.bbox.sw.lng);
            var newBBox = new google.maps.LatLngBounds(newSW, newNE);
            if(currentBBox.contains(newBBox.getNorthEast()) && currentBBox.contains(newBBox.getSouthWest())){
                for(var i=0; i<this.locations.length; i++){
                    var l = Locations.get(this.locations[i]);
                    if(l){
                        l.marker.view.highlight();
                    }
                }
            } else {
                dispatcher.once('LocationList:load', function(){
                    for(var i=0; i<this.locations.length; i++){
                        var l = Locations.get(this.locations[i]);
                        if(l){
                            l.marker.view.highlight();
                        }
                    }
                }, this);
                map.fitBounds(newBBox);
            }
        }
    });

    var MovieSuggestions = Backbone.Collection.extend({
        model: MovieSuggestion
    });

    var LocationSuggestion = Backbone.Model.extend({
        initialize: function(obj){
            this.id = obj.identifier;
            this.lat = obj.lat;
            this.lng = obj.lng;
        },
        select: function(){
            var currentCenter = map.getCenter();
            if(this.lat == currentCenter.lat() && this.lng == currentCenter.lng()){
                var loc = Locations.get(this.id);
                loc.marker.view.highlight();
            } else {
                dispatcher.once('LocationList:load', function(){
                    var loc = Locations.get(this.id);
                    if(loc){
                        loc.marker.view.highlight();
                    }
                }, this);
                var newCenter = new google.maps.LatLng(this.lat, this.lng);
                map.setCenter(newCenter);
            }
        }
    });

    var LocationSuggestions = Backbone.Collection.extend({
        model: LocationSuggestion
    });

    var SuggestionsView = Backbone.View.extend({
        el: $('#suggestions'),
        template: _.template($('#search-template').html()),
        fetchTimeout: null,
        events: {
            'click .movie.suggestion': 'highlightMovie',
            'click .location.suggestion': 'highlightLocation'
        },
        delayedFetch: function(){
            clearTimeout(this.fetchTimeout);
            var that = this;
            this.fetchTimeout = setTimeout(function () {
                that.suggest();
                that.fetchTimeout = null;
            }, 1000);
        },
        initialize: function(){
            dispatcher.on('Search:update', this.delayedFetch, this);
            this.$el.hide();
        },
        suggest: function(){
            var query = $('#search').val();
            var that = this;
            $.ajax({
                url:"/json/search",
                data: {
                    q: query,
                    city: Cities.selectedCity.id
                },
                success:function(result){
                    if(result.movies.length || result.locations.length){
                        that.$el.html(that.template(result));
                        that.movies = new MovieSuggestions(result.movies);
                        that.locations = new LocationSuggestions(result.locations);
                        that.$el.show();
                    } else {
                        that.$el.hide();
                    }
                }
            });
        },
        highlightMovie: function(ev){
            var movie = this.movies.get(ev.currentTarget.id);
            movie.select();
        },
        highlightLocation: function(ev){
            var location = this.locations.get(ev.currentTarget.id);
            location.select();
        }
    });

    var SearchView = Backbone.View.extend({
        el: $('#search'),
        events: {
            'keyup': 'keyupHandler'
        },
        keyupHandler: function(){
            dispatcher.trigger('Search:update');
        }
    });

    var Search = new SearchView;
    var Suggestions = new SuggestionsView;

    var City = Backbone.Model.extend({
        initialize: function(obj){
            this.id = obj.identifier;
            this.location = {
                lat: obj.lat,
                lng: obj.lng
            };
            this.name = obj.formatted_name;
        },
        select: function(){
            initializeMap({
                center: this.location,
                zoom: DEFAULT_ZOOM
            });
            $('#city-name').text(this.name);
        }
    });

    var CityList = Backbone.Collection.extend({
        model: City,
        url: function(){
            return '/json/cities';
        },
        select: function(city_id){
            var city = Cities.get(city_id);
            if(city){
                city.select();
                this.selectedCity = city;
            }
        }
    });

    var Cities = new CityList;

    var CityListView = Backbone.View.extend({
        el: $('#city'),
        template: _.template($('#city-template').html()),
        initialize: function(){
            this.listenTo(Cities, 'reset', this.render);
        },
        events: {
            'change': 'select'
        },
        render: function(){
            this.$el.html(this.template({'cities': Cities.toJSON()}));
        },
        select: function(ev){
            Cities.select(this.$el.val());
        }
    });

    var CityListing = new CityListView;
    Cities.fetch({
        reset: true,
        success: function(){
            Cities.select(Cities.first().id);
        }
    });

    function clearHighlighting(){
        while(active_markers.length){
            active_markers[0].view.nohighlight();
        }
    }

    $('#clear-highlight').on('click', function(e){
        clearHighlighting();
        e.preventDefault();
    });

    // Google Maps
    var map;

    function setMapWidth() {
        var mapWidth = window.innerWidth - 400;
        var mapDiv = document.getElementById('map-canvas');
        mapDiv.style.width = mapWidth + 'px';
    }

    function initializeMap(mapOptions) {
        map = new google.maps.Map(document.getElementById('map-canvas'), mapOptions);

        setMapWidth();
        google.maps.event.addDomListener(window, 'resize', setMapWidth);

        google.maps.event.addListener(map, 'bounds_changed', function () {
            Locations.delayedFetch();
        });
    }
});
