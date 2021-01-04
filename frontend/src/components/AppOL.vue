<template>
  <div style="background-color: orange">

    <!-- ========== map & view ========= -->
    <vl-map  :load-tiles-while-animating="true"
             :load-tiles-while-interacting="true"
             data-projection="EPSG:4326"
             ref="map"
              @mounted="onMapMounted"
           >

    <vl-view ref="view"
             :zoom.sync="zoom"
             :center.sync="center"
             :rotation.sync="rotation"></vl-view>

      <!-- ========== layers ========= -->
      <!-- OpenStreetMap base layer
      -->
      <vl-layer-tile id="osm">
        <vl-source-osm></vl-source-osm>
      </vl-layer-tile>

      <!-- flight path features layer - geojson file retrieval via url
          TODO: swap out default url loader for custom loader (for error checking)
          almost: https://github.com/ghettovoice/vuelayers/issues/59
          uses style function/factory to color item based on geojson properties

      -->
      <vl-layer-vector >
        <vl-source-vector :url="geojsonUrl"
                          :features.sync="geojFeatures" />
        <vl-style-func :factory="geojStyleFuncFactory"></vl-style-func>
      </vl-layer-vector>

      <!-- kml features layer
      -->
      <vl-layer-vector >
          <vl-source-vector :url="kmlUrl"
                            :format-factory="kmlFormatFactory" />
      </vl-layer-vector>

      <!-- asdex layer ==========================  -->
      <vl-layer-vector >

<!-- ============ method 1: use loader-factory ============ -->

<!-- note: PostGIS put id (which is track num) in geojson at the same
     level with type and geometry which allows this to work: -->

        <vl-source-vector
                  :features.sync="asdexFeatures"
                  :url="asdexUrl"
                  :loader-factory="loaderFactory"
                  />

<!-- ============ method 2: use v-for ============ -->

<!-- displays linestrings, but is *SLOW* (if unk included)  - - >

      <vl-source-vector ref="asdexSource">
        <vl-feature v-for="feature in asdexObject.features"
                    :key="feature.id"
                    :id="feature.id"
                    :properties="feature.properties">
          <vl-geom-line-string :coordinates="feature.geometry.coordinates" />
        </vl-feature>
        </vl-source-vector>

< ! - - ============ method end ============ -->

      <vl-style-func :factory="asdexStyleFuncFac" />

<!-- ======================================================= -->

      </vl-layer-vector>

      <!-- ========== popup =========
          note: 'display' string in geojson properties was crafted by python
      -->
   <vl-interaction-select :features.sync="geojFeatures"></vl-interaction-select>

    <vl-overlay v-for="feature in geojFeatures"
                :key="feature.id"
                :position="feature.geometry.coordinates[0]">
      <div style="background: #ccf">
        {{ feature.properties.display }}
      </div>
    </vl-overlay>

      <!-- ========== end layers ========= -->
    </vl-map>

  </div>
</template>

<script>

// $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

import ZoomSlider from 'ol/control/ZoomSlider'
import ScaleLine  from 'ol/control/ScaleLine'
import Stroke     from 'ol/style/Stroke'
import Style      from 'ol/style/Style'
import KML        from 'ol/format/KML'

import Text       from 'ol/style/Text'
import Fill       from 'ol/style/Fill'
import Circle     from 'ol/style/Circle'

import { Vector as VectorLayer } from 'ol/layer'

// ==========================================================
const highlightSt =new Style({ stroke: new Stroke({ color: 'magenta',width: 5.0 }) })
const undoStyle   =new Style({ stroke: new Stroke({ color: 'green',  width: 5.0 }) })
const src_s_style =new Style({ stroke: new Stroke({ color: 'green',  width: 3.0 }) })
const src_f_style =new Style({ stroke: new Stroke({ color: 'blue',   width: 3.0 }) })
const src_a_style =new Style({ stroke: new Stroke({ color: 'magenta',width: 3.0 }) })
const unk_style   =new Style({ stroke: new Stroke({ color: 'brown',  width: 3.0 }) })
const plainStyle  =new Style({ stroke: new Stroke({ color: 'purple', width: 3.0 }) })
const activeStyle =new Style({ stroke: new Stroke({ color: 'orange', width: 5.0 }) })
// ==========================================================

var global_asdexUrl = 'bogus';

const methods = {

// ============ method 1: use loader-factory

    loaderFactory: (vm) => (extent, resolution, projection) => {

console.log("inside loaderFactory:", vm, extent, resolution, projection);

      return fetch(global_asdexUrl)
        .then(response => response.json())
        .then(data =>  {

/* ********************* do this if $emit works:
        let dlist = [];
        for (let k = 0; k < data.features.length; k++) {
            let elem = { track:  data.features[k].properties.track,
                         acid:   data.features[k].properties.acid,
                         actype: data.features[k].properties.actype  };
            dlist.push(elem);
        }
//this.$root.$emit('dlist', (dlist) );
********************* */

        return(data);
     })
   },

    onMapMounted () {
      // now ol.Map instance is ready and we can work with it directly
      this.$refs.map.$map.getControls().extend([
        new ScaleLine(),
        new ZoomSlider(),
      ])
    },

    kmlFormatFactory () {
      return new KML()
    },

    // ------------ ASDEX attempt to color lines
    // sun pm: now works all the time, and nothing undefined:
    asdexStyleFuncFac() {

      return (feature) => {
console.log("aSFF+g:" + feature.get('track') + "," +
              this.highLightMe + ',' + feature.getGeometry().getType() );

        // ------------------------------
        let targetStyle = new Style({
          image: new Circle({
            radius: 10,
            fill: new Fill({
                color: '#fff',
            }),
            stroke: new Stroke({
              color: '#F44336',
            }),
          }),
          text: new Text({
              text: String(feature.get('acid')), // get feature property
          }),
        })
        // ------------------------------

        if (feature.getGeometry().getType() == "Point") {
              return targetStyle;
        }

        if (feature.key == this.highLightMe) {
          return activeStyle;
        }
        return plainStyle;
     }
    },
    // ------------ attempt to color lines
    geojStyleFuncFactory() {

      return (feature) => {
        if (feature.get('SOURCE_TYPE')) {
          if (feature.get('SOURCE_TYPE')=='S') { return src_s_style; }
          if (feature.get('SOURCE_TYPE')=='F') { return src_f_style; }
          if (feature.get('SOURCE_TYPE')=='A') { return src_a_style; }
          return unk_style;
        }
        return unk_style;
     }
   }
}

// ==========================================================

// center map on center of usa
var KSTL = [-90.3700289, 38.7486972];

export default {
    methods,
    data () {
      return {
        zoom: 5,
        center: KSTL,
        rotation: 0,

        geojsonUrl: '',
        geojFeatures: [],

        kmlUrl: '',

        // all OLD, INOP:
        asdexUrl: 'bogus',
        asdexFeatures: [],
        aaaFeatures: [],   // rather old: https://github.com/ghettovoice/vuelayers/issues/25
        highLightMe: 15,  // track id of item to highlight

        // NEW:
        asdexObject : {},  // the FeatureCollection
        highlightedFeat: 0
      }
    },

// ==========================================================

  mounted () {

    // ---- receive vuejs message from AppUI, insert query into reactive
    // ---- location which apparently fires off a url request
    // -------------------------
    this.$root.$on('geojsonurl', (the_query) => {
      console.log("geojson:"+the_query);

      this.geojsonUrl = the_query;   // << that's all we have to do!
    })
    // -------------------------
    this.$root.$on('kmlurl', (the_query) => {
      console.log("kml:"+the_query);

      this.kmlUrl = the_query;
    })
    // -------------------------
    this.$root.$on('highlightthis', (the_track) => {
      console.log("highlightthis rcvd:"+the_track);

      this.highLightMe = the_track;
// ================================

      // turn off the previous one:
      if (this.highlightedFeat != 0) {
          this.highlightedFeat.setStyle(undoStyle);
      }

      // find the vector layer that has a Feature with this id
      const a_layer = this.$refs.map.getLayers().filter(layer => {
        return layer instanceof VectorLayer &&
                   layer.getSource().getFeatureById(the_track)
      })

      // --------- this statement causes aSFF to fire with valid arguments
      this.highlightedFeat = a_layer[0].getSource().getFeatureById(the_track);

      this.highlightedFeat.setStyle(highlightSt);

      // ================================
    })

    // -------------------------
    this.$root.$on('asdexurl', (the_query) => {
      console.log("asdex::"+the_query);

      // NOTE: loacerFactory does the actual retrieve
      global_asdexUrl = the_query;  // Q: is there a better way to communicate this??
      this.asdexUrl = the_query;   // this fires off method 1 via vl-source-vector

//  ============ method 2: use v-for ============

      return fetch(global_asdexUrl)
        .then(response => response.json())
        .then(data =>  {
            console.log("then(data)");
            console.log(typeof data);    // FIXME: remove duplicate keys
            console.log(data);    // FIXME: remove duplicate keys

// *************** do this if loader-factory method not chosen to retrieve map data:
      // this.asdexObject = data;

// *************** do this if $emit in loader-factory method DOESN'T work:

            let dlist = [];
            for (let k = 0; k < data.features.length; k++) {
                let elem = { track:  data.features[k].properties.track,
                             acid:   data.features[k].properties.acid,
                             actype: data.features[k].properties.actype  };
                dlist.push(elem);
            }
            this.$root.$emit('dlist', (dlist) );
// =============== duplicate =================
        })
    })
  }, // ---- mounted

}

</script>

